"""Python HTTP detector"""
import re
from typing import List, Dict, Any


class PythonHTTPDetector:
    """Detects HTTP calls in Python code"""
    
    def __init__(self):
        # Patterns for common HTTP libraries
        self.patterns = [
            # requests library
            (r"requests\.(get|post|put|delete|patch|head|options)\(['\"]([^'\"]+)['\"]", "requests"),
            # httpx library - direct calls
            (r"httpx\.(get|post|put|delete|patch|head|options)\(['\"]([^'\"]+)['\"]", "httpx"),
            # httpx.Client() context manager pattern - client.get(), client.post(), etc.
            # Handles both regular strings and f-strings: client.post(f"{VAR}/path") or client.post("http://...")
            (r"client\.(get|post|put|delete|patch|head|options)\([^)]*f?['\"]([^'\"]+)['\"]", "httpx"),
            # urllib
            (r"urllib\.request\.(urlopen|Request)\(['\"]([^'\"]+)['\"]", "urllib"),
            # aiohttp
            (r"aiohttp\.ClientSession\(\)\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", "aiohttp"),
        ]
    
    def detect(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect HTTP calls in Python code"""
        findings = []
        
        for pattern, library in self.patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                method = match.group(1).upper() if match.group(1) else "GET"
                url = match.group(2) if len(match.groups()) > 1 else match.group(1)
                
                # For f-strings with variables, extract the full expression
                # e.g., f"{USER_SERVICE_URL}/users/{user_id}/validate" -> extract the path part
                # Try to extract URL from the full match if it's an f-string
                full_match = match.group(0)
                if 'f"' in full_match or "f'" in full_match:
                    # Extract the full f-string expression (everything between quotes)
                    fstring_match = re.search(r'f?["\']([^"\']+)["\']', full_match)
                    if fstring_match:
                        url_expr = fstring_match.group(1)
                        # If it contains variables like {VAR}, try to extract the path part
                        # Look for patterns like "{VAR}/path" or "/path"
                        path_match = re.search(r'/([a-z-]+(?:/[a-z-]+)*)', url_expr)
                        if path_match:
                            # Reconstruct URL with variable placeholder
                            # e.g., "{USER_SERVICE_URL}/users/{user_id}/validate" -> extract "/users/..."
                            url = url_expr
                        else:
                            url = url_expr
                
                # Get line number
                line_num = content[:match.start()].count("\n") + 1
                
                findings.append({
                    "type": "HTTP",
                    "method": method,
                    "url": url,
                    "library": library,
                    "file": file_path,
                    "line": line_num,
                    "confidence": 0.85,
                })
        
        return findings

