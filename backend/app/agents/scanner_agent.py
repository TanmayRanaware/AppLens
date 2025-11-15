"""Scanner agent for driving MCP GitHub tools"""
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from app.config import settings
from app.services.mcp_client import MCPGitHubClient


class ScannerAgent:
    """Agent that drives GitHub MCP tools to fetch code"""
    
    def __init__(self, mcp_client: MCPGitHubClient):
        self.mcp_client = mcp_client
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Code Scanner",
            goal="Fetch code files from GitHub repositories using MCP tools",
            backstory="You are a code scanning specialist who efficiently retrieves code from version control systems.",
            verbose=True,
            llm=self.llm,
        )
    
    async def scan_repository(self, repo_full_name: str, branch: str = "main") -> list:
        """Scan repository and return file list"""
        # Use MCP client directly (simplified - in production, agent would orchestrate)
        files = await self.mcp_client.list_files(repo_full_name, "", branch)
        return files

