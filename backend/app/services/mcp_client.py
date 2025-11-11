"""MCP GitHub client wrapper"""
import httpx
from typing import List, Optional, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class MCPGitHubClient:
    """Client for GitHub MCP server"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = f"http://{settings.mcp_github_host}:{settings.mcp_github_port}"
    
    async def list_files(self, repo_full_name: str, path: str = "", branch: str = "main") -> List[Dict[str, Any]]:
        """List files in a repository"""
        try:
            async with httpx.AsyncClient() as client:
                # Use GitHub API directly as fallback
                url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"token {self.access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    params={"ref": branch},
                )
                if response.status_code == 200:
                    return response.json()
                return []
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    async def get_file_content(self, repo_full_name: str, file_path: str, branch: str = "main") -> Optional[str]:
        """Get file content"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"token {self.access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    params={"ref": branch},
                )
                if response.status_code == 200:
                    import base64
                    data = response.json()
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    return content
                return None
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return None
    
    async def get_commit_sha(self, repo_full_name: str, branch: str = "main") -> Optional[str]:
        """Get commit SHA for a branch"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.github.com/repos/{repo_full_name}/commits/{branch}"
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"token {self.access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                if response.status_code == 200:
                    return response.json()["sha"]
                return None
        except Exception as e:
            logger.error(f"Error getting commit SHA: {e}")
            return None

