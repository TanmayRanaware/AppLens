"""Chat routes for AI agents"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app.routes.auth import get_current_user
from app.agents.error_agent import ErrorAgent
from app.agents.whatif_agent import WhatIfAgent
from app.db.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class ErrorAnalyzerRequest(BaseModel):
    """Request for error analyzer"""
    log_text: str


class WhatIfRequest(BaseModel):
    """Request for what-if simulator"""
    repo: str
    file_path: Optional[str] = None
    diff: Optional[str] = None
    pr_url: Optional[str] = None


@router.post("/error-analyzer")
async def error_analyzer(
    request_body: ErrorAnalyzerRequest,
    request: Request,
):
    """Analyze error logs and identify affected services"""
    user = get_current_user(request)
    
    async for session in get_db():
        agent = ErrorAgent(session)
        result = await agent.analyze(request_body.log_text)
        return result
        break


@router.post("/what-if")
async def what_if(
    request_body: WhatIfRequest,
    request: Request,
):
    """Simulate impact of code changes"""
    user = get_current_user(request)
    access_token = user.get("access_token")
    
    async for session in get_db():
        agent = WhatIfAgent(session, access_token)
        result = await agent.simulate(
            repo=request_body.repo,
            file_path=request_body.file_path,
            diff=request_body.diff,
            pr_url=request_body.pr_url,
        )
        return result
        break

