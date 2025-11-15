"""Scan routes"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List
from uuid import UUID
from app.routes.auth import get_current_user
from app.db.base import get_db
from app.db.models import Scan, ScanTarget, Repository, ScanStatus
from app.services.scan_pipeline import ScanPipeline
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

router = APIRouter()


class ScanStartRequest(BaseModel):
    """Request to start a scan"""
    repo_full_names: List[str]


@router.post("/start")
async def start_scan(
    request_body: ScanStartRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Start a new scan"""
    try:
        user = get_current_user(request)
        user_id = user.get("sub")
        access_token = user.get("access_token")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid user ID in token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No GitHub access token found. Please re-authenticate.")
        
        if not request_body.repo_full_names:
            raise HTTPException(status_code=400, detail="No repositories provided")
        
        async for session in get_db():
            try:
                # Create scan record
                scan = Scan(
                    user_id=user_id,
                    status=ScanStatus.QUEUED,
                    started_at=datetime.utcnow(),
                )
                session.add(scan)
                await session.flush()
                
                # Create scan targets
                for repo_full_name in request_body.repo_full_names:
                    # Validate repo_full_name format
                    if "/" not in repo_full_name:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Invalid repository format: {repo_full_name}. Expected format: owner/repo"
                        )
                    
                    # Get or create repository
                    result = await session.execute(
                        select(Repository).where(Repository.full_name == repo_full_name)
                    )
                    repo = result.scalar_one_or_none()
                    
                    if not repo:
                        # Create repository (simplified - in production, fetch from GitHub API)
                        owner = repo_full_name.split("/")[0]
                        repo = Repository(
                            full_name=repo_full_name,
                            html_url=f"https://github.com/{repo_full_name}",
                            owner=owner,
                        )
                        session.add(repo)
                        await session.flush()
                    
                    scan_target = ScanTarget(
                        scan_id=scan.id,
                        repo_id=repo.id,
                    )
                    session.add(scan_target)
                
                await session.commit()
                
                # Start scan in background
                async def run_scan():
                    async for db_session in get_db():
                        try:
                            pipeline = ScanPipeline(scan.id, access_token, db_session)
                            await pipeline.run()
                        except Exception as e:
                            # Error handling is done in pipeline.run()
                            pass
                        finally:
                            break
                
                background_tasks.add_task(run_scan)
                
                return {"scan_id": str(scan.id), "status": "queued"}
            except HTTPException:
                raise
            except Exception as e:
                await session.rollback()
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


@router.get("/status/{scan_id}")
async def get_scan_status(scan_id: UUID, request: Request):
    """Get scan status"""
    get_current_user(request)  # Verify auth
    
    async for session in get_db():
        result = await session.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        return {
            "scan_id": str(scan.id),
            "status": scan.status.value,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
            "error": scan.error,
        }

