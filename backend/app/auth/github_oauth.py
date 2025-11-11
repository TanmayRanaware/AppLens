"""GitHub OAuth implementation"""
import httpx
from typing import Optional
from app.config import settings


async def get_github_access_token(code: str) -> Optional[str]:
    """Exchange GitHub OAuth code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
    return None


async def get_github_user(access_token: str) -> Optional[dict]:
    """Get GitHub user information"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        if response.status_code == 200:
            return response.json()
    return None


async def get_github_user_repos(access_token: str, username: Optional[str] = None) -> list:
    """Get GitHub repositories for a user"""
    url = f"https://api.github.com/user/repos" if not username else f"https://api.github.com/users/{username}/repos"
    async with httpx.AsyncClient() as client:
        repos = []
        page = 1
        while True:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                params={"page": page, "per_page": 100, "type": "all"},
            )
            if response.status_code != 200:
                break
            page_repos = response.json()
            if not page_repos:
                break
            repos.extend(page_repos)
            page += 1
        return repos

