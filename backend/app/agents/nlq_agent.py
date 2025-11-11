"""Natural Language Query agent"""
from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings
from app.db.models import Service, Interaction, Repository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class NLQAgent:
    """Agent for processing natural language queries"""
    
    # Allowed tables and columns for safety
    ALLOWED_TABLES = {
        "services": ["id", "name", "repo_id", "language"],
        "interactions": ["id", "source_service_id", "target_service_id", "edge_type", "http_method", "http_url", "kafka_topic"],
        "repositories": ["id", "full_name", "html_url"],
    }
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Natural Language Query Processor",
            goal="Translate natural language questions into safe database queries",
            backstory="You are an expert at understanding user questions and generating safe SQL queries.",
            verbose=True,
            llm=self.llm,
        )
    
    async def query(self, question: str) -> Dict[str, Any]:
        """Process natural language query"""
        question_lower = question.lower()
        
        # Pattern matching for common queries
        if "services that call" in question_lower or "calls" in question_lower:
            return await self._query_service_calls(question)
        elif "kafka topic" in question_lower or "topic" in question_lower:
            return await self._query_kafka_topics(question)
        elif "highest in-degree" in question_lower or "most connected" in question_lower:
            return await self._query_top_services_by_degree(question)
        elif "fan-out" in question_lower or "hops" in question_lower:
            return await self._query_fanout(question)
        else:
            # Generic query - use LLM to generate safe SQL
            return await self._generic_query(question)
    
    async def _query_service_calls(self, question: str) -> Dict[str, Any]:
        """Query services that call a specific service"""
        # Extract service name from question
        match = re.search(r'call[s]?\s+([a-z-]+)', question, re.IGNORECASE)
        if not match:
            return {"error": "Could not extract service name from question"}
        
        target_service_name = match.group(1)
        
        # Find target service
        result = await self.db_session.execute(
            select(Service).where(Service.name.ilike(f"%{target_service_name}%"))
        )
        target_service = result.scalar_one_or_none()
        
        if not target_service:
            return {"results": [], "message": f"Service '{target_service_name}' not found"}
        
        # Find services that call it
        result = await self.db_session.execute(
            select(Interaction, Service).join(
                Service, Interaction.source_service_id == Service.id
            ).where(Interaction.target_service_id == target_service.id)
        )
        rows = result.all()
        
        results = []
        for interaction, service in rows:
            results.append({
                "service_name": service.name,
                "method": interaction.http_method,
                "url": interaction.http_url,
                "type": interaction.edge_type.value,
            })
        
        return {"results": results, "graph_hints": {"highlight_services": [str(target_service.id)]}}
    
    async def _query_kafka_topics(self, question: str) -> Dict[str, Any]:
        """Query Kafka topics"""
        # Extract topic name if mentioned
        match = re.search(r'topic[:\s]+([a-z0-9._-]+)', question, re.IGNORECASE)
        topic_name = match.group(1) if match else None
        
        if topic_name:
            result = await self.db_session.execute(
                select(Interaction).where(Interaction.kafka_topic == topic_name)
            )
            interactions = result.scalars().all()
            
            results = []
            for interaction in interactions:
                source_result = await self.db_session.execute(
                    select(Service).where(Service.id == interaction.source_service_id)
                )
                target_result = await self.db_session.execute(
                    select(Service).where(Service.id == interaction.target_service_id)
                )
                source = source_result.scalar_one()
                target = target_result.scalar_one()
                
                results.append({
                    "source": source.name,
                    "target": target.name,
                    "topic": interaction.kafka_topic,
                })
            
            return {"results": results}
        else:
            # List all topics
            result = await self.db_session.execute(
                select(Interaction.kafka_topic).distinct().where(Interaction.kafka_topic.isnot(None))
            )
            topics = [r[0] for r in result.all()]
            return {"results": [{"topic": t} for t in topics]}
    
    async def _query_top_services_by_degree(self, question: str) -> Dict[str, Any]:
        """Query top services by in-degree"""
        # Extract number if specified
        match = re.search(r'top\s+(\d+)', question, re.IGNORECASE)
        limit = int(match.group(1)) if match else 5
        
        # Count in-degree for each service
        result = await self.db_session.execute(
            select(
                Service.id,
                Service.name,
                func.count(Interaction.id).label("in_degree")
            ).join(
                Interaction, Service.id == Interaction.target_service_id
            ).group_by(Service.id, Service.name).order_by(
                func.count(Interaction.id).desc()
            ).limit(limit)
        )
        
        rows = result.all()
        results = []
        for service_id, name, in_degree in rows:
            results.append({
                "service_name": name,
                "in_degree": in_degree,
            })
        
        return {"results": results}
    
    async def _query_fanout(self, question: str) -> Dict[str, Any]:
        """Query fan-out patterns"""
        # Extract service name and hop count
        match = re.search(r'(\d+)\s+hop[s]?', question, re.IGNORECASE)
        hops = int(match.group(1)) if match else 2
        
        match = re.search(r'reach[es]?\s+([a-z-]+)', question, re.IGNORECASE)
        target_name = match.group(1) if match else None
        
        if not target_name:
            return {"error": "Could not extract target service name"}
        
        # Find target service
        result = await self.db_session.execute(
            select(Service).where(Service.name.ilike(f"%{target_name}%"))
        )
        target_service = result.scalar_one_or_none()
        
        if not target_service:
            return {"error": f"Service '{target_name}' not found"}
        
        # BFS to find services within N hops
        visited = {str(target_service.id)}
        current_level = [target_service.id]
        
        for _ in range(hops):
            next_level = []
            result = await self.db_session.execute(
                select(Interaction.source_service_id).where(
                    Interaction.target_service_id.in_(current_level)
                ).distinct()
            )
            for (service_id,) in result.all():
                if str(service_id) not in visited:
                    visited.add(str(service_id))
                    next_level.append(service_id)
            current_level = next_level
        
        # Get service names
        result = await self.db_session.execute(
            select(Service).where(Service.id.in_(list(visited)))
        )
        services = result.scalars().all()
        
        results = [{"service_name": s.name} for s in services]
        
        return {
            "results": results,
            "graph_hints": {"highlight_services": list(visited)},
        }
    
    async def _generic_query(self, question: str) -> Dict[str, Any]:
        """Generic query handler using LLM"""
        # In production, use LLM to generate safe SQL
        # For now, return a simple response
        return {
            "results": [],
            "message": "Generic query processing not yet implemented. Please use specific query patterns.",
        }

