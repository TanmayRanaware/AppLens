"""Code fetching service"""
from typing import List, Dict, Any
from app.services.mcp_client import MCPGitHubClient
import logging

logger = logging.getLogger(__name__)


class CodeFetchService:
    """Service for fetching code from repositories"""
    
    def __init__(self, mcp_client: MCPGitHubClient):
        self.mcp_client = mcp_client
    
    async def fetch_repo_files(
        self,
        repo_full_name: str,
        branch: str = "main",
        extensions: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all relevant files from a repository"""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".java", ".tsx", ".jsx"]
        
        files = []
        
        async def traverse_path(path: str = ""):
            """Recursively traverse repository paths"""
            items = await self.mcp_client.list_files(repo_full_name, path, branch)
            
            for item in items:
                if item["type"] == "file":
                    file_path = item["path"]
                    if any(file_path.endswith(ext) for ext in extensions):
                        content = await self.mcp_client.get_file_content(repo_full_name, file_path, branch)
                        if content:
                            files.append({
                                "path": file_path,
                                "content": content,
                                "size": item.get("size", 0),
                            })
                elif item["type"] == "dir":
                    # Skip common directories
                    dir_name = item["name"]
                    if dir_name not in [".git", "node_modules", "__pycache__", ".venv", "venv", "target", ".idea"]:
                        await traverse_path(item["path"])
        
        await traverse_path()
        return files

