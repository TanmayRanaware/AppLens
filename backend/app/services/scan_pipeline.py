"""Scan pipeline service"""
from uuid import UUID
from typing import List
from app.services.mcp_client import MCPGitHubClient
from app.services.code_fetch import CodeFetchService
from app.services.detectors.http_python import PythonHTTPDetector
from app.services.detectors.http_javascript import JavaScriptHTTPDetector
from app.services.detectors.http_java import JavaHTTPDetector
from app.services.detectors.kafka_python import PythonKafkaDetector
from app.services.detectors.kafka_java import JavaKafkaDetector
from app.services.detectors.kafka_node import NodeKafkaDetector
from app.services.graph_builder import GraphBuilder
from app.db.base import AsyncSession
from app.db.models import Scan, ScanTarget, Repository, Service, Interaction, Endpoint, ScanStatus, EdgeType, EndpointKind, Direction
from sqlalchemy import select
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ScanPipeline:
    """Pipeline for scanning repositories"""
    
    def __init__(self, scan_id: UUID, access_token: str, db_session: AsyncSession):
        self.scan_id = scan_id
        self.access_token = access_token
        self.db_session = db_session
        self.mcp_client = MCPGitHubClient(access_token)
        self.code_fetch = CodeFetchService(self.mcp_client)
        
        # Initialize detectors
        self.detectors = {
            "python": {
                "http": PythonHTTPDetector(),
                "kafka": PythonKafkaDetector(),
            },
            "javascript": {
                "http": JavaScriptHTTPDetector(),
                "kafka": NodeKafkaDetector(),
            },
            "typescript": {
                "http": JavaScriptHTTPDetector(),
                "kafka": NodeKafkaDetector(),
            },
            "java": {
                "http": JavaHTTPDetector(),
                "kafka": JavaKafkaDetector(),
            },
        }
        
        self.graph_builder = GraphBuilder()
    
    async def run(self):
        """Run the scan pipeline"""
        try:
            # Update scan status
            result = await self.db_session.execute(
                select(Scan).where(Scan.id == self.scan_id)
            )
            scan = result.scalar_one()
            scan.status = ScanStatus.RUNNING
            await self.db_session.commit()
            
            # Get scan targets
            result = await self.db_session.execute(
                select(ScanTarget).where(ScanTarget.scan_id == self.scan_id)
            )
            targets = result.scalars().all()
            
            all_findings = []
            all_services = {}  # Aggregate services from all repos
            repo_map = {}  # Map repo_id to Repository object
            
            # First pass: Collect all findings and services from all repos
            for target in targets:
                # Get repository
                repo_result = await self.db_session.execute(
                    select(Repository).where(Repository.id == target.repo_id)
                )
                repo = repo_result.scalar_one()
                repo_map[repo.id] = repo
                
                # Get commit SHA
                commit_sha = await self.mcp_client.get_commit_sha(repo.full_name, target.branch)
                if not commit_sha:
                    commit_sha = target.commit_sha or "unknown"
                
                # Fetch files
                logger.info(f"Fetching files from {repo.full_name}")
                files = await self.code_fetch.fetch_repo_files(repo.full_name, target.branch)
                
                # Run detectors
                repo_findings = []
                for file_info in files:
                    file_path = file_info["path"]
                    content = file_info["content"]
                    language = self._detect_language(file_path)
                    
                    if language in self.detectors:
                        # Run HTTP detector
                        http_findings = self.detectors[language]["http"].detect(file_path, content)
                        repo_findings.extend(http_findings)
                        
                        # Run Kafka detector
                        kafka_findings = self.detectors[language]["kafka"].detect(file_path, content)
                        repo_findings.extend(kafka_findings)
                
                # Build services for this repo
                repo_services = self.graph_builder.build_services_from_findings(
                    repo_findings, repo.full_name, commit_sha
                )
                
                # Merge services into all_services (keyed by service name)
                for service_name, service_data in repo_services.items():
                    if service_name not in all_services:
                        all_services[service_name] = service_data
                    # Keep track of which repo this service belongs to
                    all_services[service_name]["repo_id"] = repo.id
                
                # Add findings with repo context
                for finding in repo_findings:
                    finding["repo_id"] = repo.id
                    finding["repo_full_name"] = repo.full_name
                all_findings.extend(repo_findings)
            
            # Second pass: Build interactions using all services (cross-repo matching)
            all_interactions = self.graph_builder.build_interactions_from_findings(
                all_findings, all_services
            )
            
            # Third pass: Save services and interactions grouped by repo
            for repo_id, repo in repo_map.items():
                # Get services for this repo
                repo_services = {
                    name: data for name, data in all_services.items()
                    if data.get("repo_id") == repo_id
                }
                
                # Get interactions where source or target is from this repo
                repo_interactions = []
                for interaction in all_interactions:
                    source_name = interaction.get("source_service")
                    target_name = interaction.get("target_service")
                    
                    source_repo_id = all_services.get(source_name, {}).get("repo_id")
                    target_repo_id = all_services.get(target_name, {}).get("repo_id")
                    
                    # Include interaction if source or target is from this repo
                    if source_repo_id == repo_id or target_repo_id == repo_id:
                        repo_interactions.append(interaction)
                
                # Get commit SHA for this repo
                target = next(t for t in targets if t.repo_id == repo_id)
                commit_sha = await self.mcp_client.get_commit_sha(repo.full_name, target.branch)
                if not commit_sha:
                    commit_sha = target.commit_sha or "unknown"
                
                # Save to database
                await self._save_to_db(repo, all_services, repo_interactions, commit_sha)
            
            # Update scan status
            scan.status = ScanStatus.SUCCESS
            scan.finished_at = datetime.utcnow()
            await self.db_session.commit()
            
            logger.info(f"Scan {self.scan_id} completed successfully")
        
        except Exception as e:
            logger.error(f"Error in scan pipeline: {e}", exc_info=True)
            # Update scan status
            result = await self.db_session.execute(
                select(Scan).where(Scan.id == self.scan_id)
            )
            scan = result.scalar_one()
            scan.status = ScanStatus.ERROR
            scan.error = str(e)
            scan.finished_at = datetime.utcnow()
            await self.db_session.commit()
    
    async def _save_to_db(
        self,
        repo: Repository,
        all_services: dict,
        interactions: List[dict],
        commit_sha: str,
    ):
        """Save services and interactions to database"""
        service_map = {}
        
        # Create or update services (only real services from scanned repos)
        for service_name, service_data in all_services.items():
            # Get the repo_id for this service
            service_repo_id = service_data.get("repo_id")
            if not service_repo_id:
                continue  # Skip if no repo_id (shouldn't happen)
            
            # Check if service exists
            result = await self.db_session.execute(
                select(Service).where(
                    Service.name == service_name,
                    Service.repo_id == service_repo_id
                )
            )
            service = result.scalar_one_or_none()
            
            if not service:
                service = Service(
                    name=service_name,
                    repo_id=service_repo_id,
                    language=service_data.get("language"),
                    path_hint=service_data.get("path_hint"),
                    last_commit_sha=commit_sha,
                )
                self.db_session.add(service)
                await self.db_session.flush()
            
            service_map[service_name] = service
        
        # Create interactions (only between real services)
        for interaction_data in interactions:
            source_name = interaction_data.get("source_service")
            target_name = interaction_data.get("target_service")
            
            source_service = service_map.get(source_name)
            target_service = service_map.get(target_name)
            
            # Only create interaction if both services exist (real services)
            if not source_service or not target_service:
                logger.warning(
                    f"Skipping interaction {source_name} -> {target_name}: "
                    f"source={source_service is not None}, target={target_service is not None}"
                )
                continue
            
            # Check if interaction already exists (deduplicate)
            result = await self.db_session.execute(
                select(Interaction).where(
                    Interaction.source_service_id == source_service.id,
                    Interaction.target_service_id == target_service.id,
                    Interaction.edge_type == EdgeType(interaction_data["type"]),
                    Interaction.http_url == interaction_data.get("url"),
                    Interaction.kafka_topic == interaction_data.get("topic"),
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Create interaction
                interaction = Interaction(
                    source_service_id=source_service.id,
                    target_service_id=target_service.id,
                    edge_type=EdgeType(interaction_data["type"]),
                    http_method=interaction_data.get("method"),
                    http_url=interaction_data.get("url"),
                    kafka_topic=interaction_data.get("topic"),
                    confidence=interaction_data.get("confidence", 0.5),
                    evidence=interaction_data.get("file"),
                    source_repo_commit_sha=commit_sha,
                    detector_name=interaction_data.get("detector", "unknown"),
                )
                self.db_session.add(interaction)
        
        await self.db_session.commit()
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension"""
        if file_path.endswith(".py"):
            return "python"
        elif file_path.endswith((".js", ".jsx")):
            return "javascript"
        elif file_path.endswith((".ts", ".tsx")):
            return "typescript"
        elif file_path.endswith(".java"):
            return "java"
        return "unknown"

