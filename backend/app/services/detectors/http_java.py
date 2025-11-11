"""Java HTTP detector"""
import re
from typing import List, Dict, Any


class JavaHTTPDetector:
    """Detects HTTP calls in Java code"""
    
    def __init__(self):
        self.patterns = [
            # OkHttp
            (r"new\s+Request\.Builder\(\)\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", "OkHttp", None),
            # RestTemplate
            (r"restTemplate\.(getForObject|postForObject|put|delete)\(['\"]([^'\"]+)['\"]", "RestTemplate", None),
            # WebClient
            (r"webClient\.(get|post|put|delete)\(\)\.uri\(['\"]([^'\"]+)['\"]", "WebClient", None),
        ]
    
    def detect(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect HTTP calls in Java code"""
        findings = []
        
        for pattern, library, _ in self.patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                method = match.group(1).upper()
                url = match.group(2) if len(match.groups()) > 1 else match.group(1)
                
                # Normalize method names
                if "get" in method.lower():
                    method = "GET"
                elif "post" in method.lower():
                    method = "POST"
                elif "put" in method.lower():
                    method = "PUT"
                elif "delete" in method.lower():
                    method = "DELETE"
                
                line_num = content[:match.start()].count("\n") + 1
                
                findings.append({
                    "type": "HTTP",
                    "method": method,
                    "url": url,
                    "library": library,
                    "file": file_path,
                    "line": line_num,
                    "confidence": 0.80,
                })
        
        return findings

