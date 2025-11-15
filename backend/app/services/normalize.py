"""Normalization service for deduplication and service name extraction"""
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class NormalizeService:
    """Service for normalizing and deduplicating findings"""
    
    def extract_service_name_from_url(self, url: str, available_services: Dict[str, Any] = None) -> str:
        """Extract service name from URL, matching against available services"""
        # Common patterns:
        # https://auth-service.example.com/api/v1/login -> auth-service
        # http://localhost:8080/api/users -> users (from path)
        # /api/v1/billing -> billing
        # http://localhost:8003/orders/user/{user_id} -> applens-order-service
        
        # Try to extract from hostname (skip localhost, 127.0.0.1, etc.)
        hostname_match = re.search(r'://([^/]+)', url)
        if hostname_match:
            hostname = hostname_match.group(1)
            # Skip common localhost patterns - extract from path instead
            if hostname.startswith('localhost') or hostname.startswith('127.0.0.1') or ':' in hostname:
                # This is likely a localhost URL with port, extract from path instead
                pass
            else:
                # Extract service name from subdomain (e.g., auth-service.example.com)
                parts = hostname.split('.')
                if len(parts) > 0:
                    service_name = parts[0]
                    if '-service' in service_name or 'service-' in service_name:
                        # Check if this service exists in available services
                        if available_services and service_name in available_services:
                            return service_name
                        # Try normalized version
                        normalized = self.normalize_service_name(service_name)
                        if available_services:
                            for svc_name in available_services.keys():
                                if normalized in svc_name or svc_name in normalized:
                                    return svc_name
        
        # Try to extract from path and match against available services
        # Pattern: /orders/user/123 -> "orders", /api/users -> "users", /users/validate -> "users"
        # Also handles f-strings: {VAR}/users/{id}/validate -> "users"
        # First, extract the path part (everything after hostname)
        path_part = url
        if '://' in url:
            # Extract path from URL (everything after hostname)
            path_match_url = re.search(r'://[^/]+(/.*)', url)
            if path_match_url:
                path_part = path_match_url.group(1)
        elif not url.startswith('/') and '/' in url:
            # Handle f-strings like "{VAR}/users/{id}/validate" - extract path part
            # Find the first / and take everything after it
            slash_idx = url.find('/')
            if slash_idx >= 0:
                path_part = url[slash_idx:]
        
        # Now extract service name from path
        path_match = re.search(r'/(?:api|v\d+)?/?([a-z-]+)', path_part, re.IGNORECASE)
        if path_match:
            path_service = path_match.group(1).lower()
            
            # If we have available services, try to match
            if available_services:
                # Direct match
                if path_service in available_services:
                    return path_service
                
                # Try to match by substring (e.g., "orders" -> "applens-order-service")
                # Remove "applens-" prefix and "-service" suffix for matching
                for svc_name in available_services.keys():
                    svc_base = svc_name.replace('applens-', '').replace('-service', '')
                    # Check if path_service word matches the base service name
                    # e.g., "orders" matches "order" in "applens-order-service"
                    if path_service == svc_base or path_service in svc_base or svc_base in path_service:
                        return svc_name
                
                # Try fuzzy match: check if path word appears in service name
                # e.g., "orders" in "applens-order-service"
                for svc_name in available_services.keys():
                    if path_service in svc_name.lower():
                        return svc_name
                
                # Try plural/singular matching (e.g., "orders" -> "order")
                # Remove trailing 's' and try again
                if path_service.endswith('s') and len(path_service) > 1:
                    singular = path_service[:-1]
                    for svc_name in available_services.keys():
                        svc_base = svc_name.replace('applens-', '').replace('-service', '')
                        if singular == svc_base or singular in svc_base:
                            return svc_name
            
            # Fallback: return path service name
            return path_service
        
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
