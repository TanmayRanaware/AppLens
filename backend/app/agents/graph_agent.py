"""Graph agent for deduplication and normalization"""
from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings
from typing import List, Dict, Any


class GraphAgent:
    """Agent that deduplicates and normalizes edges"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Graph Builder",
            goal="Deduplicate and normalize service interactions across repositories",
            backstory="You are a data quality expert who ensures graph consistency and removes duplicates.",
            verbose=True,
            llm=self.llm,
        )
    
    async def normalize_interactions(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize and deduplicate interactions"""
        # This is a placeholder - normalization is done in NormalizeService
        return interactions

