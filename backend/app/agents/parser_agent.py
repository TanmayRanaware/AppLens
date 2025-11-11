"""Parser agent for running detectors"""
from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings
from typing import List, Dict, Any


class ParserAgent:
    """Agent that runs language-aware detectors"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Code Parser",
            goal="Extract inter-service calls (HTTP, Kafka) from code using language-aware detectors",
            backstory="You are a static analysis expert who understands multiple programming languages and can identify service interactions.",
            verbose=True,
            llm=self.llm,
        )
    
    async def parse_file(self, file_path: str, content: str, language: str) -> List[Dict[str, Any]]:
        """Parse a file and return findings"""
        # This is a placeholder - in production, the agent would coordinate detectors
        # For now, return empty list (detectors are called directly from pipeline)
        return []

