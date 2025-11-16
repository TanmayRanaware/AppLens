"""Orchestrator agent for coordinating scan phases"""
from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings


class OrchestratorAgent:
    """Orchestrator agent that coordinates scan phases"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Scan Orchestrator",
            goal="Coordinate the scanning pipeline phases: fetch, parse, normalize, and store",
            backstory="You are an experienced system architect who coordinates complex code analysis workflows.",
            verbose=True,
            llm=self.llm,
        )
    
    async def decide_phase(self, current_phase: str, context: dict) -> str:
        """Decide next phase based on current state"""
        # Simplified phase decision logic
        phases = ["fetch", "parse", "normalize", "store"]
        try:
            current_index = phases.index(current_phase)
            if current_index < len(phases) - 1:
                return phases[current_index + 1]
            return "complete"
        except ValueError:
            return "fetch"

