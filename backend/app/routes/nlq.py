"""Natural Language Query routes"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.routes.auth import get_current_user
from app.agents.nlq_agent import NLQAgent
from app.db.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class NLQRequest(BaseModel):
    """Natural language query request"""
    question: str


@router.post("/")
async def nlq_query(
    request_body: NLQRequest,
    request: Request,
):
    """Process natural language query"""
    user = get_current_user(request)
    
    async for session in get_db():
        agent = NLQAgent(session)
        result = await agent.query(request_body.question)
        return result
        break

