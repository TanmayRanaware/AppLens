"""Normalization service for deduplication and service name extraction"""
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class NormalizeService:
    """Service for normalizing and deduplicating findings"""
    
    def extract_service_name_from_url(self, url: str) -> str:
        """Extract service name from URL"""
        # Common patterns:
        # https://auth-service.example.com/api/v1/login -> auth-service
        # http://localhost:8080/api/users -> users (from path)
        # /api/v1/billing -> billing
        
        # Try to extract from hostname
        hostname_match = re.search(r'://([^/]+)', url)
        if hostname_match:
            hostname = hostname_match.group(1)
            # Extract service name from subdomain
            parts = hostname.split('.')
            if len(parts) > 0:
                service_name = parts[0]
                if '-service' in service_name or 'service-' in service_name:
                    return service_name
        
        # Try to extract from path
        path_match = re.search(r'/(?:api|v\d+)?/?([a-z-]+)', url)
        if path_match:
            return path_match.group(1)
        
        # Fallback
        return "unknown-service"
    
    def deduplicate_interactions(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate interactions based on source, target, and type"""
        seen = set()
        unique = []
        
        for interaction in interactions:
            key = (
                interaction.get("source_service"),
                interaction.get("target_service"),
                interaction.get("type"),
                interaction.get("method"),
                interaction.get("url"),
                interaction.get("topic"),
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(interaction)
        
        return unique
    
    def normalize_service_name(self, name: str) -> str:
        """Normalize service name"""
        # Convert to lowercase, replace underscores with hyphens
        normalized = name.lower().replace("_", "-")
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(service-|svc-)', '', normalized)
        normalized = re.sub(r'(-service|-svc)$', '', normalized)
        return normalized
