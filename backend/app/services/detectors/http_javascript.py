"""JavaScript/TypeScript HTTP detector"""
import re
from typing import List, Dict, Any


class JavaScriptHTTPDetector:
    """Detects HTTP calls in JavaScript/TypeScript code"""
    
    def __init__(self):
        self.patterns = [
            # fetch API
            (r"fetch\(['\"]([^'\"]+)['\"]", "fetch", "GET"),
            (r"fetch\(['\"]([^'\"]+)['\"].*?method:\s*['\"]([^'\"]+)['\"]", "fetch", None),
            # axios
            (r"axios\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", "axios", None),
            # node-fetch
            (r"fetch\(['\"]([^'\"]+)['\"]", "node-fetch", "GET"),
        ]
    
    def detect(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect HTTP calls in JavaScript/TypeScript code"""
        findings = []
        
        for pattern, library, default_method in self.patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                if library == "fetch" and default_method:
                    method = default_method
                    url = match.group(1)
                elif library == "axios":
                    method = match.group(1).upper()
                    url = match.group(2)
                else:
                    method = match.group(2).upper() if len(match.groups()) > 1 else "GET"
                    url = match.group(1)
                
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

