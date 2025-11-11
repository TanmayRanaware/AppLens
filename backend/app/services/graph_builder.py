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
        
        for finding in findings:
            file_path = finding.get("file", "")
            # Extract service name from file path (heuristic)
            # e.g., services/auth-service/main.py -> auth-service
            service_name = self._extract_service_name(file_path, repo_full_name)
            
            if service_name not in services:
                services[service_name] = {
                    "name": service_name,
                    "repo_full_name": repo_full_name,
                    "language": self._detect_language(file_path),
                    "path_hint": file_path,
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
        
        for finding in findings:
            file_path = finding.get("file", "")
            source_service = self._extract_service_name(file_path, repo_full_name)
            
            if finding["type"] == "HTTP":
                url = finding.get("url", "")
                target_service = self.normalizer.extract_service_name_from_url(url)
                
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
            
            elif finding["type"] == "Kafka":
                topic = finding.get("topic", "")
                # For Kafka, we need to match producers with consumers
                # This is a simplified version - in production, use topic-based matching
                target_service = f"service-consuming-{topic}"  # Placeholder
                
                interactions.append({
                    "source_service": source_service,
                    "target_service": target_service,
                    "type": "Kafka",
                    "topic": topic,
                    "direction": finding.get("direction"),
                    "confidence": finding.get("confidence", 0.5),
                    "file": file_path,
                    "line": finding.get("line"),
                    "detector": finding.get("library", "unknown"),
                })
        
        # Deduplicate
        interactions = self.normalizer.deduplicate_interactions(interactions)
        
        return interactions
    
    def _extract_service_name(self, file_path: str, repo_full_name: str) -> str:
        """Extract service name from file path"""
        # Heuristic: look for common service directory patterns
        parts = file_path.split("/")
        
        # Check for service-like directories
        for i, part in enumerate(parts):
            if part in ["services", "src", "app"] and i + 1 < len(parts):
                return parts[i + 1]
            if "-service" in part or "service-" in part:
                return part
        
        # Fallback: use repo name
        if repo_full_name:
            return repo_full_name.split("/")[-1]
        
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

