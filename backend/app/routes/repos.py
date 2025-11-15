"""Repository routes"""
from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
from app.routes.auth import get_current_user
from app.auth.github_oauth import get_github_user_repos
from app.db.base import get_db
from app.db.models import Repository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.get("/search")
async def search_repos(q: Optional[str] = None, request: Request = None):
    """Search repositories"""
    user = get_current_user(request)
    access_token = user.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token")
    
    # Get user's repositories
    repos = await get_github_user_repos(access_token)
    
    # Filter by query if provided
    if q:
        q_lower = q.lower()
        repos = [
            r for r in repos
            if q_lower in r["full_name"].lower() or q_lower in (r.get("description") or "").lower()
        ]
    
    # Return simplified repo info
    return {
        "repos": [
            r["full_name"]
            for r in repos
            if not r.get("private", False)  # Only public repos
        ]
    }


@router.get("/")
async def list_repos(request: Request):
    """List all repositories in database"""
    from app.db.base import get_db
    async for session in get_db():
        result = await session.execute(select(Repository))
        repos = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "full_name": r.full_name,
                "html_url": r.html_url,
                "last_scanned_at": r.last_scanned_at.isoformat() if r.last_scanned_at else None,
            }
            for r in repos
        ]

