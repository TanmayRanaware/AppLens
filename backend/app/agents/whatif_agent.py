"""What-if simulator agent"""
from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings
from app.services.mcp_client import MCPGitHubClient
from app.db.models import Service, Interaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class WhatIfAgent:
    """Agent for simulating impact of code changes"""
    
    def __init__(self, db_session: AsyncSession, access_token: str):
        self.db_session = db_session
        self.access_token = access_token
        self.mcp_client = MCPGitHubClient(access_token)
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="What-If Impact Analyzer",
            goal="Predict the blast radius of code changes across microservices",
            backstory="You are an expert at analyzing code changes and predicting their impact on distributed systems.",
            verbose=True,
            llm=self.llm,
        )
    
    async def simulate(
        self,
        repo: str,
        file_path: Optional[str] = None,
        diff: Optional[str] = None,
        pr_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate impact of code changes"""
        changed_files = []
        changed_services = []
        
        if pr_url:
            # Extract repo and PR number from URL
            # e.g., https://github.com/org/repo/pull/123
            parts = pr_url.split("/")
            if len(parts) >= 7 and parts[5] == "pull":
                repo_full_name = f"{parts[3]}/{parts[4]}"
                pr_number = parts[6]
                # In production, use GitHub API to get PR files
                # For now, use placeholder
                changed_files = [f"{repo_full_name}/changed_file.py"]
        elif file_path:
            changed_files = [file_path]
        
        # Find services affected by changed files
        for file_path in changed_files:
            # Extract service name from file path
            service_name = self._extract_service_from_path(file_path)
            changed_services.append(service_name)
        
        # Find interactions for changed services
        predicted_nodes = []
        predicted_edges = []
        
        for service_name in changed_services:
            # Find service in database
            result = await self.db_session.execute(
                select(Service).where(Service.name.ilike(f"%{service_name}%"))
            )
            services = result.scalars().all()
            
            for service in services:
                service_id = str(service.id)
                predicted_nodes.append(service_id)
                
                # Find outgoing interactions (1-hop)
                result = await self.db_session.execute(
                    select(Interaction).where(Interaction.source_service_id == service.id)
                )
                outgoing = result.scalars().all()
                
                for interaction in outgoing:
                    target_id = str(interaction.target_service_id)
                    predicted_nodes.append(target_id)
                    predicted_edges.append({
                        "source": service_id,
                        "target": target_id,
                    })
                    
                    # Find 2-hop neighbors
                    result2 = await self.db_session.execute(
                        select(Interaction).where(Interaction.source_service_id == interaction.target_service_id)
                    )
                    two_hop = result2.scalars().all()
                    for interaction2 in two_hop:
                        predicted_nodes.append(str(interaction2.target_service_id))
        
        # Deduplicate
        predicted_nodes = list(set(predicted_nodes))
        
        reasoning = f"Analyzed {len(changed_files)} changed files affecting {len(changed_services)} services. Predicted impact on {len(predicted_nodes)} services within 2 hops."
        
        return {
            "predicted_impacted_nodes": predicted_nodes,
            "predicted_impacted_edges": predicted_edges,
            "reasoning": reasoning,
            "confidence": 0.75,
        }
    
    def _extract_service_from_path(self, file_path: str) -> str:
        """Extract service name from file path"""
        parts = file_path.split("/")
        for i, part in enumerate(parts):
            if part in ["services", "src", "app"] and i + 1 < len(parts):
                return parts[i + 1]
            if "-service" in part:
                return part
        return parts[0] if parts else "unknown"

