"""Natural Language Query agent"""
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from app.config import settings
from app.db.models import Service, Interaction, Repository
from app.services.mcp_client import MCPGitHubClient
from app.services.code_fetch import CodeFetchService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
import logging
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class NLQAgent:
    """Agent for processing natural language queries with CrewAI"""
    
    def __init__(self, db_session: AsyncSession, mcp_client: Optional[MCPGitHubClient] = None):
        self.db_session = db_session
        self.mcp_client = mcp_client
        self.code_fetch = CodeFetchService(mcp_client) if mcp_client else None
        
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Microservice Knowledge Assistant",
            goal="Answer questions about microservices, their dependencies, connections, and code by querying the database and GitHub repositories",
            backstory="""You are an expert assistant that helps users understand their microservice architecture. 
            You have access to:
            1. A database containing services, interactions (HTTP and Kafka), and repositories
            2. GitHub repositories for all microservices in the graph
            
            You can answer questions about:
            - Which services exist and their details
            - How services are connected (HTTP calls, Kafka topics)
            - Service dependencies and relationships
            - Code details from GitHub repositories
            - Service health, traffic patterns, and architecture
            
            Always provide clear, helpful answers with specific details when available.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False,
        )
    
    async def query(self, question: str) -> Dict[str, Any]:
        """Process natural language query using CrewAI"""
        try:
            logger.info(f"Processing NLQ question: {question[:100]}...")
            
            # Step 1: Gather context from database
            context = await self._gather_context(question)
            logger.info(f"Gathered context: {len(context['services'])} services, {len(context['interactions'])} interactions")
            
            # Step 2: Use CrewAI to answer the question
            answer = await self._answer_with_crewai(question, context)
            
            if not answer or answer.startswith("I encountered an error"):
                logger.warning(f"CrewAI returned error or empty answer: {answer}")
            
            return {
                "message": answer,
                "answer": answer,
            }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error in NLQ query: {e}\n{error_trace}", exc_info=True)
            return {
                "error": f"Error processing query: {str(e)}",
                "message": f"I encountered an error while processing your question: {str(e)}. Please try rephrasing it or check the backend logs for details.",
                "answer": f"I encountered an error while processing your question: {str(e)}. Please try rephrasing it or check the backend logs for details.",
            }
    
    async def _gather_context(self, question: str) -> Dict[str, Any]:
        """Gather relevant context from database and GitHub"""
        context = {
            "services": [],
            "interactions": [],
            "repositories": [],
        }
        
        try:
            # Get all services
            result = await self.db_session.execute(select(Service))
            services = result.scalars().all()
            context["services"] = [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "language": s.language,
                    "repo_id": str(s.repo_id),
                }
                for s in services
            ]
            
            # Get all interactions
            result = await self.db_session.execute(select(Interaction))
            interactions = result.scalars().all()
            context["interactions"] = []
            for i in interactions:
                # Get service names
                source_result = await self.db_session.execute(
                    select(Service).where(Service.id == i.source_service_id)
                )
                target_result = await self.db_session.execute(
                    select(Service).where(Service.id == i.target_service_id)
                )
                source = source_result.scalar_one_or_none()
                target = target_result.scalar_one_or_none()
                
                if source and target:
                    context["interactions"].append({
                        "source": source.name,
                        "target": target.name,
                        "type": i.edge_type.value,
                        "http_method": i.http_method,
                        "http_url": i.http_url,
                        "kafka_topic": i.kafka_topic,
                    })
            
            # Get all repositories
            result = await self.db_session.execute(select(Repository))
            repositories = result.scalars().all()
            context["repositories"] = [
                {
                    "id": str(r.id),
                    "full_name": r.full_name,
                    "html_url": r.html_url,
                    "default_branch": r.default_branch,
                }
                for r in repositories
            ]
            
        except Exception as e:
            logger.error(f"Error gathering context: {e}")
        
        return context
    
    async def _answer_with_crewai(self, question: str, context: Dict[str, Any]) -> str:
        """Use CrewAI to answer the question with context"""
        # Format context for the agent
        context_text = f"""
DATABASE CONTEXT:

Services ({len(context['services'])} total):
{chr(10).join([f"  - {s['name']} (ID: {s['id']}, Language: {s.get('language', 'unknown')})" for s in context['services'][:50]])}
{f"... and {len(context['services']) - 50} more services" if len(context['services']) > 50 else ""}

Interactions ({len(context['interactions'])} total):
{chr(10).join([f"  - {i['source']} -> {i['target']} ({i['type']})" + (f" - {i.get('http_url', i.get('kafka_topic', ''))}" if i.get('http_url') or i.get('kafka_topic') else "") for i in context['interactions'][:50]])}
{f"... and {len(context['interactions']) - 50} more interactions" if len(context['interactions']) > 50 else ""}

Repositories ({len(context['repositories'])} total):
{chr(10).join([f"  - {r['full_name']} (Branch: {r.get('default_branch', 'main')})" for r in context['repositories'][:20]])}
{f"... and {len(context['repositories']) - 20} more repositories" if len(context['repositories']) > 20 else ""}

GITHUB ACCESS:
{"Available - Can fetch code from repositories" if self.mcp_client else "Not available - No GitHub access token"}
"""
        
        task_description = f"""
Answer the following question about the microservice architecture:

Question: {question}

{context_text}

Instructions:
1. Use the database context provided above to answer the question
2. If you need code details from GitHub repositories, mention that you can access them but focus on the database information first
3. Provide a clear, helpful answer with specific details
4. If the question asks about specific services, mention their names, connections, and relevant details
5. If the question is about dependencies, explain the relationships clearly
6. Be conversational and helpful - this is a chat interface
7. Format URLs to be concise - use paths like /users/{{user_id}}/validate instead of full URLs
8. Keep lines under 80 characters when possible to fit in the chat box
9. Break long lists into multiple lines with proper indentation

Answer the question directly and clearly. Format your response to be readable in a chat interface.
"""
        
        task = Task(
            description=task_description,
            agent=self.agent,
        )
        
        try:
            def run_crew():
                try:
                    crew = Crew(
                        agents=[self.agent],
                        tasks=[task],
                        verbose=True,
                    )
                    result = crew.kickoff()
                    return result
                except Exception as e:
                    logger.error(f"Error in CrewAI execution: {e}", exc_info=True)
                    raise
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result_crew = await loop.run_in_executor(executor, run_crew)
            
            if not result_crew:
                logger.warning("CrewAI returned None result")
                return "I couldn't generate an answer. Please try rephrasing your question."
            
            answer = str(result_crew)
            if not answer or answer.strip() == "":
                logger.warning("CrewAI returned empty answer")
                return "I couldn't generate an answer. Please try rephrasing your question."
            
            # Format the answer to fit in chat box
            try:
                answer = self._format_answer_for_chat(answer)
            except Exception as e:
                logger.warning(f"Error formatting answer, using unformatted: {e}")
                # Continue with unformatted answer if formatting fails
            
            return answer
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error running CrewAI agent: {e}\n{error_trace}", exc_info=True)
            return f"I encountered an error while processing your question: {str(e)}. Please try rephrasing it."
    
    def _format_url(self, url: str, max_length: int = 50) -> str:
        """Format URL to fit in chat box"""
        if not url:
            return ""
        if url.startswith('http://') or url.startswith('https://'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path
            if path:
                url = path
        
        if '{' in url:
            url = re.sub(r'^\{[^}]+\}', '', url)
            if url and not url.startswith('/'):
                url = '/' + url
            url = re.sub(r'\{[^}]+\}', '{...}', url)
        
        if len(url) > max_length:
            if '/' in url:
                parts = url.split('/')
                if len(parts) > 2:
                    return f"/{parts[1]}/.../{parts[-1]}"
            return url[:max_length-3] + "..."
        return url
    
    def _format_answer_for_chat(self, answer: str, max_line_length: int = 80) -> str:
        """Format answer to fit within chat box by wrapping long lines and formatting URLs"""
        if not answer:
            return answer
        
        try:
            lines = answer.split('\n')
            formatted_lines = []
            
            for line in lines:
                try:
                    # Format URLs in the line
                    # Match URLs like {SERVICE_URL}/path or http://... or /path
                    url_pattern = r'(\{[A-Z_]+\_SERVICE_URL\}[^\s\)]+|https?://[^\s\)]+|/[^\s\)]+)'
                    
                    def replace_url(match):
                        try:
                            url = match.group(1)
                            formatted = self._format_url(url, max_length=50)
                            return formatted
                        except Exception:
                            return match.group(0)  # Return original if formatting fails
                    
                    line = re.sub(url_pattern, replace_url, line)
                    
                    # Wrap long lines
                    if len(line) > max_line_length:
                        words = line.split(' ')
                        current_line = []
                        current_length = 0
                        
                        for word in words:
                            word_length = len(word)
                            if current_length + word_length + 1 > max_line_length and current_line:
                                formatted_lines.append(' '.join(current_line))
                                current_line = [word]
                                current_length = word_length
                            else:
                                current_line.append(word)
                                current_length += word_length + 1
                        
                        if current_line:
                            formatted_lines.append(' '.join(current_line))
                    else:
                        formatted_lines.append(line)
                except Exception as e:
                    # If formatting a line fails, just add it as-is
                    logger.warning(f"Error formatting line, using as-is: {e}")
                    formatted_lines.append(line)
            
            return '\n'.join(formatted_lines)
        except Exception as e:
            logger.error(f"Error in _format_answer_for_chat: {e}")
            return answer  # Return original answer if formatting fails completely

