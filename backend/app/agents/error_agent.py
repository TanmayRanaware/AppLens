"""Error analyzer agent"""
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from app.config import settings
from app.db.models import Service, Interaction, LogPaste, Implication
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List
import re
import logging

logger = logging.getLogger(__name__)


class ErrorAgent:
    """Agent for analyzing error logs and identifying affected services"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Error Log Analyzer",
            goal="Analyze error logs to identify affected microservices and their dependencies",
            backstory="You are an expert at analyzing system logs and tracing errors across microservice architectures.",
            verbose=True,
            llm=self.llm,
        )
    
    async def analyze(self, log_text: str) -> Dict[str, Any]:
        """Analyze error log and return affected services"""
        # Extract service names, URLs, topics from log
        service_names = self._extract_service_names(log_text)
        urls = self._extract_urls(log_text)
        topics = self._extract_kafka_topics(log_text)
        
        # Find matching services in database
        affected_nodes = []
        affected_edges = []
        
        # Search for services by name
        for name in service_names:
            result = await self.db_session.execute(
                select(Service).where(Service.name.ilike(f"%{name}%"))
            )
            services = result.scalars().all()
            for service in services:
                affected_nodes.append(str(service.id))
        
        # Search for interactions by URL
        for url in urls:
            result = await self.db_session.execute(
                select(Interaction).where(Interaction.http_url.ilike(f"%{url}%"))
            )
            interactions = result.scalars().all()
            for interaction in interactions:
                affected_edges.append({
                    "source": str(interaction.source_service_id),
                    "target": str(interaction.target_service_id),
                })
                affected_nodes.append(str(interaction.source_service_id))
                affected_nodes.append(str(interaction.target_service_id))
        
        # Search for interactions by Kafka topic
        for topic in topics:
            result = await self.db_session.execute(
                select(Interaction).where(Interaction.kafka_topic == topic)
            )
            interactions = result.scalars().all()
            for interaction in interactions:
                affected_edges.append({
                    "source": str(interaction.source_service_id),
                    "target": str(interaction.target_service_id),
                })
                affected_nodes.append(str(interaction.source_service_id))
                affected_nodes.append(str(interaction.target_service_id))
        
        # Deduplicate
        affected_nodes = list(set(affected_nodes))
        
        # Generate reasoning
        reasoning = f"Found {len(service_names)} service references, {len(urls)} URLs, and {len(topics)} Kafka topics in the log."
        
        return {
            "affected_nodes": affected_nodes,
            "affected_edges": affected_edges,
            "reasoning": reasoning,
            "confidence": 0.7,
        }
    
    def _extract_service_names(self, log_text: str) -> List[str]:
        """Extract service names from log text"""
        # Common patterns: service-name, service_name, serviceName
        patterns = [
            r'([a-z]+(?:-[a-z]+)+-service)',
            r'([a-z]+_service)',
            r'(service[:\s]+([a-z-]+))',
        ]
        names = set()
        for pattern in patterns:
            matches = re.findall(pattern, log_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    names.add(match[-1] if match[-1] else match[0])
                else:
                    names.add(match)
        return list(names)
    
    def _extract_urls(self, log_text: str) -> List[str]:
        """Extract URLs from log text"""
        url_pattern = r'https?://[^\s]+|/[a-z0-9/_-]+'
        matches = re.findall(url_pattern, log_text)
        return matches[:10]  # Limit to 10 URLs
    
    def _extract_kafka_topics(self, log_text: str) -> List[str]:
        """Extract Kafka topic names from log text"""
        patterns = [
            r'topic[:\s]+([a-z0-9._-]+)',
            r'kafka[:\s]+([a-z0-9._-]+)',
        ]
        topics = set()
        for pattern in patterns:
            matches = re.findall(pattern, log_text, re.IGNORECASE)
            topics.update(matches)
        return list(topics)

