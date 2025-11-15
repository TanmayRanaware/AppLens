"""Graph builder service"""
from typing import List, Dict, Any
from app.services.normalize import NormalizeService
import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Service for building graph from detected interactions"""
    
    def __init__(self):
        self.normalizer = NormalizeService()
    
    def build_services_from_findings(
        self,
        findings: List[Dict[str, Any]],
        repo_full_name: str,
        commit_sha: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Build service map from findings"""
        services = {}
        
        # Always use repository name as service name (consistent with _extract_service_name)
        # This ensures one repo = one service name
        repo_service_name = self._extract_service_name("", repo_full_name)
        
        # Try to detect language and path_hint from findings
        language = "unknown"
        path_hint = ""
        for finding in findings:
            file_path = finding.get("file", "")
            if file_path:
                language = self._detect_language(file_path)
                path_hint = file_path
                break
        
        # Create single service for this repo
        services[repo_service_name] = {
            "name": repo_service_name,
            "repo_full_name": repo_full_name,
            "language": language,
            "path_hint": path_hint or repo_full_name,
            "last_commit_sha": commit_sha,
        }
        
        return services
    
    def build_interactions_from_findings(
        self,
        findings: List[Dict[str, Any]],
        services: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build interactions from findings"""
        interactions = []
        
        # Get repo_full_name from first service if available
        repo_full_name = ""
        if services:
            first_service = next(iter(services.values()))
            repo_full_name = first_service.get("repo_full_name", "")
        
        # Separate Kafka producers and consumers by topic
        kafka_producers = {}  # topic -> list of (service, finding)
        kafka_consumers = {}  # topic -> list of (service, finding)
        
        for finding in findings:
            file_path = finding.get("file", "")
            # Get repo_full_name from finding if available, otherwise use the one passed to function
            finding_repo_full_name = finding.get("repo_full_name", repo_full_name)
            source_service = self._extract_service_name(file_path, finding_repo_full_name)
            
            # Only process if source_service exists in our services (real repo)
            if source_service not in services:
                continue
            
            if finding["type"] == "HTTP":
                url = finding.get("url", "")
                # Pass available services to help with matching
                target_service = self.normalizer.extract_service_name_from_url(url, available_services=services)
                
                # Only create interaction if target_service exists in our services (real repo)
                if target_service in services:
                    interactions.append({
                        "source_service": source_service,
                        "target_service": target_service,
                        "type": "HTTP",
                        "method": finding.get("method"),
                        "url": url,
                        "confidence": finding.get("confidence", 0.5),
                        "file": file_path,
                        "line": finding.get("line"),
                        "detector": finding.get("library", "unknown"),
                    })
                else:
                    # Log when HTTP interaction is skipped due to unmatched service
                    logger.warning(
                        f"Skipping HTTP interaction: {source_service} -> {target_service} "
                        f"(URL: {url}). Target service not found in scanned services. "
                        f"Available services: {list(services.keys())}"
                    )
            
            elif finding["type"] == "Kafka":
                topic = finding.get("topic", "")
                direction = finding.get("direction", "producer")  # producer or consumer
                
                if not topic:
                    continue
                
                # Store producer/consumer by topic for later matching
                if direction == "producer":
                    if topic not in kafka_producers:
                        kafka_producers[topic] = []
                    kafka_producers[topic].append((source_service, finding))
                elif direction == "consumer":
                    if topic not in kafka_consumers:
                        kafka_consumers[topic] = []
                    kafka_consumers[topic].append((source_service, finding))
        
        # Match Kafka producers with consumers (only if both are in scanned services)
        for topic, producers in kafka_producers.items():
            consumers = kafka_consumers.get(topic, [])
            
            # Create edges: producer -> consumer (only for services in our scanned repos)
            for producer_service, producer_finding in producers:
                for consumer_service, consumer_finding in consumers:
                    # Only create edge if both services are in our scanned services
                    if producer_service in services and consumer_service in services:
                        interactions.append({
                            "source_service": producer_service,
                            "target_service": consumer_service,
                            "type": "Kafka",
                            "topic": topic,
                            "direction": "producer->consumer",
                            "confidence": min(producer_finding.get("confidence", 0.5), consumer_finding.get("confidence", 0.5)),
                            "file": producer_finding.get("file", ""),
                            "line": producer_finding.get("line"),
                            "detector": producer_finding.get("library", "unknown"),
                        })
        
        # Deduplicate
        interactions = self.normalizer.deduplicate_interactions(interactions)
        
        return interactions
    
    def _extract_service_name(self, file_path: str, repo_full_name: str) -> str:
        """Extract service name from repository name (consistent naming)"""
        # Always use repository name as service name for consistency
        # This ensures one repo = one service name, avoiding duplicates
        if repo_full_name:
            # Extract repo name from "owner/repo-name" format
            repo_name = repo_full_name.split("/")[-1]
            return repo_name
        
        return "unknown-service"
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        if file_path.endswith(".py"):
            return "python"
        elif file_path.endswith((".js", ".jsx")):
            return "javascript"
        elif file_path.endswith((".ts", ".tsx")):
            return "typescript"
        elif file_path.endswith(".java"):
            return "java"
        return "unknown"

