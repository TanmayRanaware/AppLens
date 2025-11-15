"""What-if simulator agent"""
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from app.config import settings
from app.services.mcp_client import MCPGitHubClient
from app.services.code_fetch import CodeFetchService
from app.services.detectors.http_python import PythonHTTPDetector
from app.services.detectors.http_javascript import JavaScriptHTTPDetector
from app.services.detectors.http_java import JavaHTTPDetector
from app.services.detectors.kafka_python import PythonKafkaDetector
from app.services.detectors.kafka_java import JavaKafkaDetector
from app.services.detectors.kafka_node import NodeKafkaDetector
from app.db.models import Service, Interaction, Repository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any, List, Optional, Set
import logging
import asyncio
import uuid
import re
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class WhatIfAgent:
    """Agent for simulating impact of code changes and predicting blast radius"""
    
    def __init__(self, db_session: AsyncSession, mcp_client: Optional[MCPGitHubClient] = None):
        self.db_session = db_session
        self.mcp_client = mcp_client
        self.code_fetch = CodeFetchService(mcp_client) if mcp_client else None
        
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
        
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="What-If Impact Analyzer",
            goal="Analyze code changes and predict blast radius and risk hotspots across microservices by analyzing GitHub repositories",
            backstory="You are an expert at analyzing code changes, understanding their impact on distributed systems, and predicting which services will be affected. You understand HTTP APIs, Kafka events, database changes, and service dependencies. You analyze code from GitHub repositories to identify actual connections between services.",
            verbose=True,
            llm=self.llm,
            allow_delegation=False,
        )
    
    async def simulate(
        self,
        change_description: str,
        repo: Optional[str] = None,
        file_path: Optional[str] = None,
        diff: Optional[str] = None,
        pr_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate impact of code changes and predict blast radius"""
        try:
            # Step 1: CrewAI analyzes the change description to identify primarily affected services
            analysis_result = await self._analyze_change_with_crewai(change_description, diff, file_path, pr_url)
            
            # Step 2: Extract changed service names from analysis
            changed_service_names = analysis_result.get("changed_services", [])
            if not changed_service_names:
                # Fallback: try to extract from change description
                changed_service_names = self._extract_service_names(change_description)
            
            if not changed_service_names:
                return {
                    "error": "Could not identify changed services from the change description",
                    "reasoning": analysis_result.get("analysis", "Analysis completed but no services identified"),
                }
            
            logger.info(f"Identified changed services: {changed_service_names}")
            
            # Step 3: Find changed services in database
            changed_services = []
            for service_name in changed_service_names:
                service = await self._find_service_by_name(service_name)
                if service:
                    changed_services.append(service)
            
            if not changed_services:
                return {
                    "error": f"Changed services {changed_service_names} not found in database",
                    "reasoning": analysis_result.get("analysis", ""),
                }
            
            # Step 4: Find blast radius
            # For incoming connections (services that call the changed service): Use database
            # For outgoing connections (services that the changed service calls): Scan GitHub repo
            blast_radius_nodes = set()
            blast_radius_edges = []
            blast_radius_details = {}  # {service_id: {type, url, topic, reason, file_path, line}}
            
            for changed_service in changed_services:
                logger.info(f"Analyzing service: {changed_service.name}")
                
                # First, find services that call the changed service (incoming connections) from database
                # This is more efficient than scanning all repos
                await self._find_incoming_connections_from_db(
                    changed_service,
                    blast_radius_nodes,
                    blast_radius_edges,
                    blast_radius_details,
                )
                
                # Then, scan the changed service's repo to find what it calls (outgoing connections)
                repo_result = await self.db_session.execute(
                    select(Repository).where(Repository.id == changed_service.repo_id)
                )
                repository = repo_result.scalar_one_or_none()
                
                if repository and self.mcp_client:
                    logger.info(f"Scanning repository for outgoing connections: {repository.full_name}")
                    await self._scan_service_repo(
                        changed_service,
                        repository,
                        blast_radius_nodes,
                        blast_radius_edges,
                        blast_radius_details,
                    )
                else:
                    logger.warning(f"Repository not found or MCP client not available for {changed_service.name}, using database for outgoing connections")
                    # Fallback: find outgoing connections from database
                    await self._find_outgoing_connections_from_db(
                        changed_service,
                        blast_radius_nodes,
                        blast_radius_edges,
                        blast_radius_details,
                    )
            
            # Step 5: Deduplicate and filter blast radius edges
            # Only keep edges that directly connect changed services to blast radius services
            # An edge should have: one end = changed service, other end = blast radius service
            changed_service_ids_set = {str(s.id) for s in changed_services}
            deduplicated_blast_radius_edges = []
            seen_edges = set()
            
            logger.info(f"Before deduplication: {len(blast_radius_edges)} edges, changed services: {changed_service_ids_set}, blast radius: {blast_radius_nodes}")
            
            for edge in blast_radius_edges:
                source_id = str(edge['source'])
                target_id = str(edge['target'])
                edge_key = f"{source_id}-{target_id}"
                
                # Only include edges where:
                # - Source is changed service AND target is in blast radius, OR
                # - Target is changed service AND source is in blast radius
                # DO NOT include edges between two blast radius services (unless one is also changed)
                source_is_changed = source_id in changed_service_ids_set
                target_is_changed = target_id in changed_service_ids_set
                source_is_blast = source_id in blast_radius_nodes
                target_is_blast = target_id in blast_radius_nodes
                
                # Edge must connect changed service to blast radius service
                # Exclude edges where both ends are in blast radius but neither is changed
                if ((source_is_changed and target_is_blast) or 
                    (target_is_changed and source_is_blast)):
                    if edge_key not in seen_edges:
                        deduplicated_blast_radius_edges.append(edge)
                        seen_edges.add(edge_key)
                        logger.info(f"  Included edge: {source_id} -> {target_id} (source_changed={source_is_changed}, target_changed={target_is_changed})")
                else:
                    logger.info(f"  Excluded edge: {source_id} -> {target_id} (not connecting changed to blast radius)")
            
            blast_radius_edges = deduplicated_blast_radius_edges
            logger.info(f"After deduplication: {len(blast_radius_edges)} edges connecting changed services to blast radius")
            
            # Step 6: Find risk hotspots (services with high impact potential)
            risk_hotspot_nodes = set()
            risk_hotspot_details = {}
            
            # Risk hotspots are services that:
            # 1. Are in the blast radius
            # 2. Have many incoming connections (high in-degree) - many services depend on them
            # 3. Have critical dependencies
            
            for node_id in blast_radius_nodes:
                # Count how many services depend on this service
                result = await self.db_session.execute(
                    select(Interaction).where(Interaction.target_service_id == uuid.UUID(node_id))
                )
                incoming_count = len(result.scalars().all())
                
                # Count how many services this service depends on
                result = await self.db_session.execute(
                    select(Interaction).where(Interaction.source_service_id == uuid.UUID(node_id))
                )
                outgoing_count = len(result.scalars().all())
                
                # Calculate risk score (high in-degree = high risk)
                risk_score = incoming_count + (outgoing_count * 0.5)  # Incoming is more critical
                
                # Mark as risk hotspot if it has significant dependencies
                if risk_score >= 2 or incoming_count >= 2:
                    risk_hotspot_nodes.add(node_id)
                    
                    if node_id not in risk_hotspot_details:
                        service = await self._get_service_by_id(node_id)
                        service_name = service.name if service else f"Service {node_id[:8]}"
                        risk_hotspot_details[node_id] = {
                            "risk_score": risk_score,
                            "incoming_connections": incoming_count,
                            "outgoing_connections": outgoing_count,
                            "reason": f"High risk hotspot: {incoming_count} services depend on {service_name}, {outgoing_count} dependencies",
                        }
            
            # Step 7: Get service names
            service_id_to_name = {}
            changed_service_names_list = [s.name for s in changed_services]
            for service in changed_services:
                service_id_to_name[str(service.id)] = service.name
            
            blast_radius_service_names = []
            if blast_radius_nodes:
                try:
                    uuid_ids = [uuid.UUID(id) for id in blast_radius_nodes]
                    result = await self.db_session.execute(
                        select(Service).where(Service.id.in_(uuid_ids))
                    )
                    services = result.scalars().all()
                    blast_radius_service_names = [s.name for s in services]
                    service_id_to_name.update({str(s.id): s.name for s in services})
                except Exception as e:
                    logger.error(f"Error converting service IDs to UUIDs: {e}")
            
            risk_hotspot_service_names = []
            if risk_hotspot_nodes:
                try:
                    uuid_ids = [uuid.UUID(id) for id in risk_hotspot_nodes]
                    result = await self.db_session.execute(
                        select(Service).where(Service.id.in_(uuid_ids))
                    )
                    services = result.scalars().all()
                    risk_hotspot_service_names = [s.name for s in services]
                    service_id_to_name.update({str(s.id): s.name for s in services})
                except Exception as e:
                    logger.error(f"Error converting service IDs to UUIDs: {e}")
            
            # Step 7: Build reasoning with detailed proof
            reasoning = self._build_reasoning(
                analysis_result,
                changed_service_names_list,
                blast_radius_service_names,
                risk_hotspot_service_names,
                blast_radius_nodes,
                risk_hotspot_nodes,
                blast_radius_edges,
                blast_radius_details,
                risk_hotspot_details,
                service_id_to_name,
            )
            
            return {
                "changed_services": changed_service_names_list,
                "changed_service_ids": [str(s.id) for s in changed_services],
                "blast_radius_nodes": list(blast_radius_nodes),
                "blast_radius_service_names": blast_radius_service_names,
                "blast_radius_edges": blast_radius_edges,
                "risk_hotspot_nodes": list(risk_hotspot_nodes),
                "risk_hotspot_service_names": risk_hotspot_service_names,
                "reasoning": reasoning,
                "analysis": analysis_result.get("analysis", ""),
                "confidence": 0.8,
            }
        except Exception as e:
            logger.error(f"Error in simulate method: {e}", exc_info=True)
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Full traceback: {error_trace}")
            return {
                "error": f"Error analyzing change: {str(e)}",
                "reasoning": f"An error occurred while analyzing the change.\n\nError: {str(e)}\n\nPlease check the backend logs for full details.",
                "changed_services": [],
                "blast_radius_nodes": [],
                "risk_hotspot_nodes": [],
                "blast_radius_edges": [],
            }
    
    async def _scan_service_repo(
        self,
        changed_service: Service,
        repository: Repository,
        blast_radius_nodes: Set[str],
        blast_radius_edges: List[Dict],
        blast_radius_details: Dict[str, Dict],
    ):
        """Scan a service's GitHub repository to find actual connections"""
        try:
            logger.info(f"Fetching files from {repository.full_name}")
            files = await self.code_fetch.fetch_repo_files(repository.full_name, repository.default_branch or "main")
            
            changed_service_id = str(changed_service.id)
            all_findings = []
            
            # Run detectors on all files
            for file_info in files:
                file_path = file_info["path"]
                content = file_info["content"]
                language = self._detect_language(file_path)
                
                if language in self.detectors:
                    # Run HTTP detector
                    http_findings = self.detectors[language]["http"].detect(file_path, content)
                    for finding in http_findings:
                        finding["repo_full_name"] = repository.full_name
                        finding["type"] = "HTTP"
                    all_findings.extend(http_findings)
                    
                    # Run Kafka detector
                    kafka_findings = self.detectors[language]["kafka"].detect(file_path, content)
                    for finding in kafka_findings:
                        finding["repo_full_name"] = repository.full_name
                        finding["type"] = "KAFKA"
                    all_findings.extend(kafka_findings)
            
            logger.info(f"Found {len(all_findings)} findings in {repository.full_name}")
            
            # Match findings to services in database
            seen_edges = set()  # Track edges by (source, target) tuple
            for finding in all_findings:
                # For HTTP findings, try to match URL to target service
                if finding.get("type") == "HTTP":
                    url = finding.get("url", "")
                    target_service = await self._match_url_to_service(url)
                    if target_service and str(target_service.id) != changed_service_id:
                        target_id = str(target_service.id)
                        blast_radius_nodes.add(target_id)
                        edge_key = (changed_service_id, target_id)
                        if edge_key not in seen_edges:
                            blast_radius_edges.append({
                                "source": changed_service_id,
                                "target": target_id,
                                "type": "HTTP",
                            })
                            seen_edges.add(edge_key)
                        
                        if target_id not in blast_radius_details:
                            blast_radius_details[target_id] = {
                                "type": "HTTP",
                                "url": url,
                                "topic": None,
                                "reason": f"Changed service {changed_service.name} calls it via HTTP",
                                "file_path": finding.get("file_path", ""),
                                "line": finding.get("line", 0),
                            }
                
                # For Kafka findings, try to match topic to consumer services
                elif finding.get("type") == "KAFKA":
                    topic = finding.get("topic", "")
                    if finding.get("kind") == "producer":
                        # Find services that consume this topic
                        consumer_services = await self._find_kafka_consumers(topic)
                        for consumer_service in consumer_services:
                            if str(consumer_service.id) != changed_service_id:
                                consumer_id = str(consumer_service.id)
                                blast_radius_nodes.add(consumer_id)
                                edge_key = (changed_service_id, consumer_id)
                                if edge_key not in seen_edges:
                                    blast_radius_edges.append({
                                        "source": changed_service_id,
                                        "target": consumer_id,
                                        "type": "KAFKA",
                                    })
                                    seen_edges.add(edge_key)
                                
                                if consumer_id not in blast_radius_details:
                                    blast_radius_details[consumer_id] = {
                                        "type": "KAFKA",
                                        "url": None,
                                        "topic": topic,
                                        "reason": f"Changed service {changed_service.name} produces to topic '{topic}' which this service consumes",
                                        "file_path": finding.get("file_path", ""),
                                        "line": finding.get("line", 0),
                                    }
                    elif finding.get("kind") == "consumer":
                        # Find services that produce this topic
                        producer_services = await self._find_kafka_producers(topic)
                        for producer_service in producer_services:
                            if str(producer_service.id) != changed_service_id:
                                producer_id = str(producer_service.id)
                                blast_radius_nodes.add(producer_id)
                                edge_key = (producer_id, changed_service_id)
                                if edge_key not in seen_edges:
                                    blast_radius_edges.append({
                                        "source": producer_id,
                                        "target": changed_service_id,
                                        "type": "KAFKA",
                                    })
                                    seen_edges.add(edge_key)
                                
                                if producer_id not in blast_radius_details:
                                    blast_radius_details[producer_id] = {
                                        "type": "KAFKA",
                                        "url": None,
                                        "topic": topic,
                                        "reason": f"Changed service {changed_service.name} consumes topic '{topic}' which this service produces",
                                        "file_path": finding.get("file_path", ""),
                                        "line": finding.get("line", 0),
                                    }
        
        except Exception as e:
            logger.error(f"Error scanning repository {repository.full_name}: {e}", exc_info=True)
            # Fallback to database for outgoing connections
            await self._find_outgoing_connections_from_db(changed_service, blast_radius_nodes, blast_radius_edges, blast_radius_details)
    
    async def _find_incoming_connections_from_db(
        self,
        changed_service: Service,
        blast_radius_nodes: Set[str],
        blast_radius_edges: List[Dict],
        blast_radius_details: Dict[str, Dict],
    ):
        """Find services that call the changed service (incoming connections) from database"""
        changed_service_id = str(changed_service.id)
        
        # Find services that depend on the changed service (callers)
        result = await self.db_session.execute(
            select(Interaction).where(Interaction.target_service_id == uuid.UUID(changed_service_id))
        )
        interactions = result.scalars().all()
        
        logger.info(f"Found {len(interactions)} incoming connections for {changed_service.name}")
        
        for interaction in interactions:
            caller_id = str(interaction.source_service_id)
            blast_radius_nodes.add(caller_id)
            blast_radius_edges.append({
                "source": caller_id,
                "target": changed_service_id,
                "type": interaction.edge_type.value,
            })
            if caller_id not in blast_radius_details:
                blast_radius_details[caller_id] = {
                    "type": interaction.edge_type.value,
                    "url": interaction.http_url,
                    "topic": interaction.kafka_topic,
                    "reason": f"Calls changed service {changed_service.name} via {interaction.edge_type.value}",
                }
    
    async def _find_outgoing_connections_from_db(
        self,
        changed_service: Service,
        blast_radius_nodes: Set[str],
        blast_radius_edges: List[Dict],
        blast_radius_details: Dict[str, Dict],
    ):
        """Find services that the changed service calls (outgoing connections) from database"""
        changed_service_id = str(changed_service.id)
        
        # Find services that the changed service depends on (targets)
        result = await self.db_session.execute(
            select(Interaction).where(Interaction.source_service_id == uuid.UUID(changed_service_id))
        )
        interactions = result.scalars().all()
        
        logger.info(f"Found {len(interactions)} outgoing connections for {changed_service.name}")
        
        for interaction in interactions:
            target_id = str(interaction.target_service_id)
            blast_radius_nodes.add(target_id)
            blast_radius_edges.append({
                "source": changed_service_id,
                "target": target_id,
                "type": interaction.edge_type.value,
            })
            if target_id not in blast_radius_details:
                blast_radius_details[target_id] = {
                    "type": interaction.edge_type.value,
                    "url": interaction.http_url,
                    "topic": interaction.kafka_topic,
                    "reason": f"Changed service {changed_service.name} calls it via {interaction.edge_type.value}",
                }
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file path"""
        if file_path.endswith(".py"):
            return "python"
        elif file_path.endswith((".js", ".jsx")):
            return "javascript"
        elif file_path.endswith((".ts", ".tsx")):
            return "typescript"
        elif file_path.endswith((".java", ".kt")):
            return "java"
        return "unknown"
    
    async def _match_url_to_service(self, url: str) -> Optional[Service]:
        """Match HTTP URL to a target service"""
        if not url:
            return None
        
        # Extract service name from URL patterns
        # Patterns: http://user-service/..., {USER_SERVICE_URL}/..., /users/...
        service_name_patterns = [
            r"://([a-z-]+(?:-service)?)",
            r"\{([A-Z_]+)_SERVICE_URL\}",
            r"/([a-z-]+(?:-service)?)/",
        ]
        
        for pattern in service_name_patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                potential_name = match.group(1).lower().replace("_", "-")
                if not potential_name.endswith("-service"):
                    potential_name = f"{potential_name}-service"
                
                # Try to find service
                service = await self._find_service_by_name(potential_name)
                if service:
                    return service
        
        # Try to find by endpoint path
        # Extract path from URL and try to match to services
        path_match = re.search(r"/([a-z-]+)/", url)
        if path_match:
            path_service = path_match.group(1)
            potential_name = f"{path_service}-service"
            service = await self._find_service_by_name(potential_name)
            if service:
                return service
        
        return None
    
    async def _find_kafka_consumers(self, topic: str) -> List[Service]:
        """Find services that consume a Kafka topic"""
        from app.db.models import EdgeType
        result = await self.db_session.execute(
            select(Interaction).where(
                and_(
                    Interaction.kafka_topic == topic,
                    Interaction.edge_type == EdgeType.KAFKA
                )
            )
        )
        interactions = result.scalars().all()
        
        consumer_services = []
        seen_service_ids = set()
        for interaction in interactions:
            # Consumer is the target service
            if interaction.target_service_id not in seen_service_ids:
                result = await self.db_session.execute(
                    select(Service).where(Service.id == interaction.target_service_id)
                )
                service = result.scalar_one_or_none()
                if service:
                    consumer_services.append(service)
                    seen_service_ids.add(interaction.target_service_id)
        
        return consumer_services
    
    async def _find_kafka_producers(self, topic: str) -> List[Service]:
        """Find services that produce to a Kafka topic"""
        from app.db.models import EdgeType
        result = await self.db_session.execute(
            select(Interaction).where(
                and_(
                    Interaction.kafka_topic == topic,
                    Interaction.edge_type == EdgeType.KAFKA
                )
            )
        )
        interactions = result.scalars().all()
        
        producer_services = []
        seen_service_ids = set()
        for interaction in interactions:
            # Producer is the source service
            if interaction.source_service_id not in seen_service_ids:
                result = await self.db_session.execute(
                    select(Service).where(Service.id == interaction.source_service_id)
                )
                service = result.scalar_one_or_none()
                if service:
                    producer_services.append(service)
                    seen_service_ids.add(interaction.source_service_id)
        
        return producer_services
    
    async def _analyze_change_with_crewai(
        self,
        change_description: str,
        diff: Optional[str] = None,
        file_path: Optional[str] = None,
        pr_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Use CrewAI to analyze the change description"""
        task_description = f"""
        Analyze the following code change and identify which services are primarily affected:
        
        Change Description: {change_description}
        """
        
        if diff:
            task_description += f"\n\nCode Diff:\n{diff}"
        if file_path:
            task_description += f"\n\nChanged File: {file_path}"
        if pr_url:
            task_description += f"\n\nPR URL: {pr_url}"
        
        task_description += """
        
        From this change, identify:
        1. What services are being changed? (Service names - be specific and exact)
        2. What type of changes are being made? (API changes, database changes, configuration changes, etc.)
        3. Why are these services affected? (Explain the connection to the change)
        4. What is the potential impact? (Breaking changes, new features, bug fixes, etc.)
        
        IMPORTANT:
        - Extract the exact service names being changed (e.g., "user-service", "payment-service", "applens-cart-service")
        - Identify any HTTP endpoints being modified
        - Identify any Kafka topics being changed
        - Focus on services that are directly mentioned or clearly connected to the change
        - Be specific about why each service is affected
        
        Format your response with clear sections explaining what services are affected and why.
        """
        
        task = Task(
            description=task_description,
            agent=self.agent,
        )
        
        try:
            def run_crew():
                crew = Crew(
                    agents=[self.agent],
                    tasks=[task],
                    verbose=True,
                )
                return crew.kickoff()
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result_crew = await loop.run_in_executor(executor, run_crew)
            
            analysis_text = str(result_crew) if result_crew else "Analysis completed."
            changed_services = self._extract_changed_services_from_analysis(analysis_text, change_description)
            
            return {
                "analysis": analysis_text,
                "changed_services": changed_services,
            }
        except Exception as e:
            logger.error(f"Error running CrewAI agent: {e}")
            changed_services = self._extract_service_names(change_description)
            return {
                "analysis": f"Change analysis failed: {str(e)}. Extracted service names: {', '.join(changed_services)}",
                "changed_services": changed_services,
            }
    
    async def _find_service_by_name(self, service_name: str) -> Optional[Service]:
        """Find service in database by name"""
        logger.info(f"Searching for service: '{service_name}'")
        
        # Try exact match first
        result = await self.db_session.execute(
            select(Service).where(Service.name == service_name)
        )
        service = result.scalar_one_or_none()
        
        if service:
            logger.info(f"Found exact match: {service.name} (ID: {service.id})")
            return service
        
        # Try case-insensitive exact match
        result = await self.db_session.execute(
            select(Service).where(Service.name.ilike(service_name))
        )
        service = result.scalar_one_or_none()
        
        if service:
            logger.info(f"Found case-insensitive match: {service.name} (ID: {service.id})")
            return service
        
        # Try partial match
        result = await self.db_session.execute(
            select(Service).where(Service.name.ilike(f"%{service_name}%"))
        )
        services = result.scalars().all()
        
        if services:
            # Prefer services that end with the service name
            for s in services:
                if s.name.lower().endswith(service_name.lower()):
                    logger.info(f"Found partial match (ends with): {s.name} (ID: {s.id})")
                    return s
            logger.info(f"Found partial match: {services[0].name} (ID: {services[0].id})")
            return services[0]
        
        logger.warning(f"Service '{service_name}' not found in database")
        return None
    
    async def _get_service_by_id(self, service_id: str) -> Optional[Service]:
        """Get service by ID"""
        try:
            result = await self.db_session.execute(
                select(Service).where(Service.id == uuid.UUID(service_id))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting service by ID: {e}")
            return None
    
    def _extract_changed_services_from_analysis(self, analysis_text: str, change_description: str) -> List[str]:
        """Extract changed service names from CrewAI analysis"""
        patterns = [
            r'services? being changed[:\s]+(?:is\s+)?(?:the\s+)?["\']?([a-z-]+(?:-service)?)["\']?',
            r'changed services?[:\s]+(?:is\s+)?(?:the\s+)?["\']?([a-z-]+(?:-service)?)["\']?',
            r'service[:\s]+(?:is\s+)?(?:the\s+)?["\']?([a-z-]+(?:-service)?)["\']?',
            r'["\']([a-z-]+(?:-service)?)["\']',
            r'([a-z-]+(?:-service)?)',
        ]
        
        services = set()
        for pattern in patterns:
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[-1]
                # Filter out common false positives
                if match and match not in ['the', 'is', 'are', 'being', 'changed', 'service']:
                    services.add(match.lower())
        
        logger.info(f"Extracted services from analysis: {services}")
        
        # Fallback to change description
        if not services:
            services = set(self._extract_service_names(change_description))
            logger.info(f"Fallback: Extracted services from description: {services}")
        
        return list(services)
    
    def _extract_service_names(self, text: str) -> List[str]:
        """Extract service names from text"""
        patterns = [
            r'([a-z]+(?:-[a-z]+)+-service)',
            r'([a-z]+_service)',
            r'(service[:\s]+([a-z-]+))',
        ]
        names = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    names.add(match[-1] if match[-1] else match[0])
                else:
                    names.add(match)
        return list(names)
    
    def _format_url(self, url: str, max_length: int = 45) -> str:
        """Format URL to fit in chat box"""
        if not url:
            return ""
        if url.startswith('http://') or url.startswith('https://'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path
            if path:
                url = path
        
        if '{' in url:
            import re
            url = re.sub(r'^\{[^}]+\}', '', url)
            if url and not url.startswith('/'):
                url = '/' + url
            url = re.sub(r'\{[^}]+\}', '{...}', url)
        
        if len(url) > max_length:
            if '/' in url:
                parts = url.split('/')
                if len(parts) > 2:
                    return f"/{parts[1]}/.../{parts[-1]}"
            return url[:max_length-3] + "..."
        return url
    
    def _build_reasoning(
        self,
        analysis_result: Dict[str, Any],
        changed_service_names: List[str],
        blast_radius_service_names: List[str],
        risk_hotspot_service_names: List[str],
        blast_radius_nodes: set,
        risk_hotspot_nodes: set,
        blast_radius_edges: List[Dict],
        blast_radius_details: Dict,
        risk_hotspot_details: Dict,
        service_id_to_name: Dict[str, str],
    ) -> str:
        """Build detailed reasoning with proof"""
        
        # Build connections list
        connections_list = ""
        if blast_radius_edges:
            for edge in blast_radius_edges[:15]:
                source_name = service_id_to_name.get(str(edge['source']), f"Service {str(edge['source'])[:8]}")
                target_name = service_id_to_name.get(str(edge['target']), f"Service {str(edge['target'])[:8]}")
                connections_list += f"  - {source_name} -> {target_name} ({edge.get('type', 'HTTP')})\n"
            if len(blast_radius_edges) > 15:
                connections_list += f"  - ... and {len(blast_radius_edges) - 15} more connection(s)\n"
        
        # Build proof sections
        blast_radius_proof = ""
        if blast_radius_service_names:
            blast_radius_proof = "\nBLAST RADIUS - DETAILED PROOF\n\n"
            for service_id, details in blast_radius_details.items():
                service_name = service_id_to_name.get(service_id, f"Service {service_id[:8]}")
                blast_radius_proof += f"{service_name}\n"
                blast_radius_proof += f"  - Connection Type: {details['type']}\n"
                if details.get('url'):
                    formatted_url = self._format_url(details['url'])
                    blast_radius_proof += f"  - HTTP Endpoint: {formatted_url}\n"
                if details.get('topic'):
                    blast_radius_proof += f"  - Kafka Topic: {details['topic']}\n"
                if details.get('file_path'):
                    blast_radius_proof += f"  - Found in: {details['file_path']}"
                    if details.get('line'):
                        blast_radius_proof += f" (line {details['line']})"
                    blast_radius_proof += "\n"
                blast_radius_proof += f"  - Why in Blast Radius: {details['reason']}\n\n"
        
        risk_hotspot_proof = ""
        if risk_hotspot_service_names:
            risk_hotspot_proof = "\nRISK HOTSPOTS - DETAILED PROOF\n\n"
            for service_id, details in risk_hotspot_details.items():
                service_name = service_id_to_name.get(service_id, f"Service {service_id[:8]}")
                risk_hotspot_proof += f"{service_name}\n"
                risk_hotspot_proof += f"  - Risk Score: {details.get('risk_score', 0):.1f}\n"
                risk_hotspot_proof += f"  - Incoming Connections: {details.get('incoming_connections', 0)}\n"
                risk_hotspot_proof += f"  - Outgoing Connections: {details.get('outgoing_connections', 0)}\n"
                risk_hotspot_proof += f"  - Why Risk Hotspot: {details['reason']}\n\n"
        
        reasoning = f"""{analysis_result.get("analysis", "Analysis completed")}

GRAPH VISUALIZATION

Changed Services (BLUE Nodes - Primary):
{', '.join(changed_service_names) if changed_service_names else "None identified"}

These services are marked BLUE because they are being modified by the change (primary nodes).

Blast Radius (RED Nodes - Directly Affected):
Total: {len(blast_radius_service_names)} service(s) in blast radius

Services:
{chr(10).join([f"  - {name}" for name in blast_radius_service_names]) if blast_radius_service_names else "  - None found - No services are directly affected by this change."}

These services are marked RED because they are directly affected by the changes (they depend on changed services or changed services depend on them).

Risk Hotspots (RED Nodes - High Risk):
Total: {len(risk_hotspot_service_names)} service(s) identified as risk hotspots

Services:
{chr(10).join([f"  - {name}" for name in risk_hotspot_service_names]) if risk_hotspot_service_names else "  - None found - No high-risk services identified."}

These services are marked RED as risk hotspots because they have high impact potential (many services depend on them or they have critical dependencies). They are part of the blast radius.

Affected Connections (RED Edges):
Total: {len(blast_radius_edges)} connection(s) affected

{connections_list if connections_list else "  - No connections found."}

{blast_radius_proof}
{risk_hotspot_proof}
HOW TO MITIGATE RISK

1. Review the changed services and their dependencies
2. Test all services in the blast radius before deployment
3. Pay special attention to risk hotspots - consider staged rollouts
4. Monitor services in the blast radius after deployment
5. Have rollback plan ready for critical changes
"""
        
        return reasoning
