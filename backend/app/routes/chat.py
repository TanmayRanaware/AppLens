"""Chat routes for AI agents"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging
from app.routes.auth import get_current_user
from app.agents.error_agent import ErrorAgent
from app.agents.whatif_agent import WhatIfAgent
from app.agents.nlq_agent import NLQAgent
from app.db.base import get_db
from app.services.mcp_client import MCPGitHubClient
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


class ErrorAnalyzerRequest(BaseModel):
    """Request for error analyzer"""
    log_text: str


class WhatIfRequest(BaseModel):
    """Request for what-if simulator"""
    change_description: str  # User's description of the change
    repo: Optional[str] = None
    file_path: Optional[str] = None
    diff: Optional[str] = None
    pr_url: Optional[str] = None


class NLQRequest(BaseModel):
    """Request for NLQ (Ask Me)"""
    question: str


@router.post("/error-analyzer")
async def error_analyzer(
    request_body: ErrorAnalyzerRequest,
    request: Request,
):
    """Analyze error logs and identify affected services"""
    try:
        user = get_current_user(request)
        access_token = user.get("access_token")
        
        async for session in get_db():
            # Create MCP client for GitHub scanning if needed
            mcp_client = None
            if access_token:
                try:
                    mcp_client = MCPGitHubClient(access_token)
                except Exception as e:
                    logger.warning(f"Could not create MCP client: {e}")
            
            agent = ErrorAgent(session, mcp_client=mcp_client)
            result = await agent.analyze(request_body.log_text)
            return result
    except Exception as e:
        logger.error(f"Error in error_analyzer endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing log: {str(e)}")


@router.post("/what-if")
async def what_if(
    request_body: WhatIfRequest,
    request: Request,
):
    """Simulate impact of code changes and predict blast radius"""
    try:
        user = get_current_user(request)
        access_token = user.get("access_token")
        
        async for session in get_db():
            mcp_client = None
            if access_token:
                try:
                    mcp_client = MCPGitHubClient(access_token)
                except Exception as e:
                    logger.warning(f"Could not create MCP client: {e}")
            
            agent = WhatIfAgent(session, mcp_client=mcp_client)
            result = await agent.simulate(
                change_description=request_body.change_description,
                repo=request_body.repo,
                file_path=request_body.file_path,
                diff=request_body.diff,
                pr_url=request_body.pr_url,
            )
            return result
    except Exception as e:
        logger.error(f"Error in what_if endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing change: {str(e)}")


@router.post("/nlq")
async def nlq(
    request_body: NLQRequest,
    request: Request,
):
    """Answer questions about microservices using CrewAI"""
    try:
        user = get_current_user(request)
        access_token = user.get("access_token")
        
        async for session in get_db():
            mcp_client = None
            if access_token:
                try:
                    mcp_client = MCPGitHubClient(access_token)
                except Exception as e:
                    logger.warning(f"Could not create MCP client: {e}")
            
            agent = NLQAgent(session, mcp_client=mcp_client)
            result = await agent.query(request_body.question)
            return result
    except Exception as e:
        logger.error(f"Error in nlq endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

