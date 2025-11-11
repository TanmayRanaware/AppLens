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
            # httpx library
            (r"httpx\.(get|post|put|delete|patch|head|options)\(['\"]([^'\"]+)['\"]", "httpx"),
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

