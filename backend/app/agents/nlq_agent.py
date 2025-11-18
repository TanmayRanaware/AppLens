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


def clean_text_for_chat(text: str) -> str:
    """Remove emojis and extraneous characters to make text human-readable"""
    if not text:
        return text
    
    # Remove emojis using regex (covers most Unicode emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Remove excessive markdown formatting (keep basic structure)
    # Remove triple backticks (code blocks) but keep content
    text = re.sub(r'```[a-z]*\n?', '', text)
    text = re.sub(r'```', '', text)
    
    # Remove excessive asterisks/bold formatting (keep single asterisks for emphasis if needed)
    # Replace multiple asterisks with single space
    text = re.sub(r'\*{2,}', ' ', text)
    
    # Remove excessive underscores
    text = re.sub(r'_{2,}', ' ', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
    text = re.sub(r' {2,}', ' ', text)  # Max 1 space between words
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove leading/trailing whitespace from entire text
    text = text.strip()
    
    return text


class NLQAgent:
    """Agent for processing natural language queries with CrewAI"""
    
    def __init__(self, db_session: AsyncSession, mcp_client: Optional[MCPGitHubClient] = None):
        self.db_session = db_session
        self.mcp_client = mcp_client
        self.code_fetch = CodeFetchService(mcp_client) if mcp_client else None
        
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Microservice Knowledge Assistant",
            goal="Answer questions about microservices, their dependencies, connections, and code by querying the database and GitHub repositories. When error analysis context is provided, answer questions about that analysis without running a new one.",
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
            - Previous error analysis results (when context is provided)
            
            IMPORTANT: When a user asks a follow-up question about a previous error analysis (indicated by PREVIOUS ERROR ANALYSIS CONTEXT), you should:
            - Answer the specific question using ONLY the provided error analysis context
            - Do NOT run a new error analysis
            - Do NOT analyze new error logs
            - Do NOT generate new ERROR ANALYSIS sections
            - Only reference and explain what's already in the provided context
            
            Always provide clear, helpful answers with specific details when available.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False,
        )
    
    async def query(self, question: str, error_analysis_context: Optional[Dict[str, Any]] = None, what_if_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process natural language query using CrewAI
        
        Args:
            question: User's question
            error_analysis_context: Optional context from a previous error analysis to help answer questions about it
            what_if_context: Optional context from a previous what-if analysis to help answer questions about it
        """
        try:
            logger.info(f"Processing NLQ question: {question[:100]}...")
            if error_analysis_context:
                logger.info(f"🔍 FOLLOW-UP QUESTION DETECTED: Using error analysis context for follow-up question")
                logger.info(f"   Primary service: {error_analysis_context.get('primary_service_name', 'Unknown')}")
                logger.info(f"   Has reasoning: {bool(error_analysis_context.get('reasoning'))}")
                logger.info(f"   Question: {question}")
            elif what_if_context:
                logger.info(f"🔍 FOLLOW-UP QUESTION DETECTED: Using what-if context for follow-up question")
                logger.info(f"   Primary service: {what_if_context.get('primary_service_name', 'Unknown')}")
                logger.info(f"   Has reasoning: {bool(what_if_context.get('reasoning'))}")
                logger.info(f"   Question: {question}")
            else:
                logger.info(f"⚠️ No analysis context - this is a regular question")
            
            # Step 1: Gather context from database
            context = await self._gather_context(question)
            logger.info(f"Gathered context: {len(context['services'])} services, {len(context['interactions'])} interactions")
            
            # Add error analysis context if provided (for follow-up questions)
            if error_analysis_context:
                context["error_analysis"] = error_analysis_context
            
            # Add what-if context if provided (for follow-up questions)
            if what_if_context:
                context["what_if_analysis"] = what_if_context
            
            # Step 2: Use CrewAI to answer the question
            answer = await self._answer_with_crewai(question, context, error_analysis_context=error_analysis_context, what_if_context=what_if_context)
            
            if not answer or answer.startswith("I encountered an error"):
                logger.warning(f"CrewAI returned error or empty answer: {answer}")
            
            # Clean text to remove emojis and extraneous characters
            clean_answer = clean_text_for_chat(answer)
            
            return {
                "message": clean_answer,
                "answer": clean_answer,
            }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error in NLQ query: {e}\n{error_trace}", exc_info=True)
            error_message = f"I encountered an error while processing your question: {str(e)}. Please try rephrasing it or check the backend logs for details."
            clean_error = clean_text_for_chat(error_message)
            
            return {
                "error": f"Error processing query: {str(e)}",
                "message": clean_error,
                "answer": clean_error,
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
    
    async def _answer_with_crewai(self, question: str, context: Dict[str, Any], error_analysis_context: Optional[Dict[str, Any]] = None, what_if_context: Optional[Dict[str, Any]] = None) -> str:
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

        # Add error analysis context if available (for follow-up questions about error analysis)
        error_analysis_text = ""
        if context.get("error_analysis"):
            error_ctx = context["error_analysis"]
            error_analysis_text = f"""

═══════════════════════════════════════════════════════════════
PREVIOUS ERROR ANALYSIS CONTEXT (USE THIS TO ANSWER QUESTIONS)
═══════════════════════════════════════════════════════════════

CRITICAL: The user is asking a follow-up question about a PREVIOUS error analysis that was already completed. 
DO NOT run a new error analysis. DO NOT analyze new error logs. 
ONLY answer questions about the error analysis results shown below.

Previous Error Analysis Results:

Primary Affected Service: {error_ctx.get('primary_service_name', error_ctx.get('source_service_name', 'Unknown'))}
Primary Service ID: {error_ctx.get('primary_node', error_ctx.get('source_node', 'Unknown'))}

Dependent Services ({len(error_ctx.get('dependent_service_names', error_ctx.get('affected_service_names', [])))} total): 
{', '.join(error_ctx.get('dependent_service_names', error_ctx.get('affected_service_names', [])))}
Dependent Service IDs: {', '.join([str(id) for id in error_ctx.get('dependent_nodes', error_ctx.get('affected_nodes', []))])}

Affected Connections ({len(error_ctx.get('affected_edges', []))} total):
{chr(10).join([f"  - {edge.get('source')} -> {edge.get('target')} ({edge.get('type', 'HTTP')})" for edge in error_ctx.get('affected_edges', [])[:20]])}

Full Error Analysis Reasoning and Explanation:
{error_ctx.get('reasoning', error_ctx.get('analysis', 'No reasoning provided'))}

═══════════════════════════════════════════════════════════════
"""
        
        # Add what-if analysis context if available (for follow-up questions about what-if analysis)
        what_if_analysis_text = ""
        if context.get("what_if_analysis"):
            what_if_ctx = context["what_if_analysis"]
            what_if_analysis_text = f"""

═══════════════════════════════════════════════════════════════
PREVIOUS WHAT-IF ANALYSIS CONTEXT (USE THIS TO ANSWER QUESTIONS)
═══════════════════════════════════════════════════════════════

CRITICAL: The user is asking a follow-up question about a PREVIOUS what-if analysis that was already completed. 
DO NOT run a new what-if analysis. DO NOT analyze new changes. 
ONLY answer questions about the what-if analysis results shown below.

Previous What-If Analysis Results:

Changed Service (Primary): {what_if_ctx.get('primary_service_name', what_if_ctx.get('source_service_name', 'Unknown'))}
Changed Service ID: {what_if_ctx.get('primary_node', what_if_ctx.get('source_node', 'Unknown'))}

Blast Radius Services ({len(what_if_ctx.get('dependent_service_names', what_if_ctx.get('affected_service_names', [])))} total): 
{', '.join(what_if_ctx.get('dependent_service_names', what_if_ctx.get('affected_service_names', [])))}
Blast Radius Service IDs: {', '.join([str(id) for id in what_if_ctx.get('dependent_nodes', what_if_ctx.get('affected_nodes', []))])}

Affected Connections ({len(what_if_ctx.get('affected_edges', []))} total):
{chr(10).join([f"  - {edge.get('source')} -> {edge.get('target')} ({edge.get('type', 'HTTP')})" for edge in what_if_ctx.get('affected_edges', [])[:20]])}

Full What-If Analysis Reasoning and Explanation:
{what_if_ctx.get('reasoning', what_if_ctx.get('analysis', 'No reasoning provided'))}

═══════════════════════════════════════════════════════════════
"""
        
        # Simplified prompt for follow-up questions about error analysis or what-if analysis
        if error_analysis_text or what_if_analysis_text:
            # When analysis context is provided, use a much simpler, direct prompt
            analysis_type = "error analysis" if error_analysis_text else "what-if analysis"
            analysis_context_text = error_analysis_text if error_analysis_text else what_if_analysis_text
            
            task_description = f"""
You are answering a follow-up question about a PREVIOUS {analysis_type} that was already completed.

Question: {question}

PREVIOUS {analysis_type.upper()} CONTEXT (use this to answer):
{analysis_context_text}

CRITICAL INSTRUCTIONS:
- This is NOT a request to analyze a new {"error" if error_analysis_text else "change"}
- This is NOT a request to run {"error analysis" if error_analysis_text else "what-if analysis"}
- DO NOT write "{analysis_type.upper()}" sections
- DO NOT include sections like "PRIMARY AFFECTED SERVICE", "DEPENDENT SERVICES", "BLAST RADIUS", etc.
- DO NOT analyze new {"logs" if error_analysis_text else "changes"}
- ONLY answer the specific question asked: "{question}"

Answer Format:
- Start directly with your answer (no headers like "{analysis_type.upper()}")
- Reference the PREVIOUS {analysis_type.upper()} CONTEXT above
- Be concise and conversational
- Just explain why the service was identified (or whatever the question asks)
- Do not repeat the entire analysis

Example answer format (EXACTLY how you should respond):
{"According to the previous error analysis, review-service was identified as the primary service because the error log showed a database connection timeout occurring in review-service at line 142 when attempting to execute a SELECT query. The error log explicitly states 'review-service.app' as the source of the error, which is why it was marked as the primary affected service." if error_analysis_text else "According to the previous what-if analysis, user-service was identified as the changed service because the change description mentioned modifying the user authentication endpoint. The analysis found that this change will affect order-service and cart-service because they depend on user-service for user validation."}

IMPORTANT:
- Your response should look like the example above - conversational, direct, and concise
- Do NOT start with "{analysis_type.upper()}" or any headers
- Do NOT include sections like "PRIMARY AFFECTED SERVICE", "DEPENDENT SERVICES", "BLAST RADIUS", etc.
- Do NOT repeat the entire analysis output
- Just answer the question in 2-4 sentences using the context provided above

Now answer this question in the format shown above: {question}
"""
        else:
            task_description = f"""
Answer the following question about the microservice architecture:

Question: {question}

{context_text}{what_if_analysis_text}

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
        
        # Create task - must be outside if/else so it's always defined
        task = Task(
            description=task_description,
            agent=self.agent,
            expected_output="A direct, conversational answer to the question (2-4 sentences) without analysis sections or headers" if (error_analysis_text or what_if_analysis_text) else "A clear, helpful answer about the microservice architecture",
        )
        
        try:
            def run_crew():
                try:
                    crew = Crew(
                        agents=[self.agent],
                        tasks=[task],
                        verbose=True,
                        max_iter=2 if (error_analysis_text or what_if_analysis_text) else 3,  # Limit iterations for follow-up questions to prevent over-analysis
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
            
            # If analysis context was provided, strip out any analysis sections that shouldn't be there
            if error_analysis_context or what_if_context or context.get("error_analysis") or context.get("what_if_analysis"):
                analysis_type = "error analysis" if (error_analysis_context or context.get("error_analysis")) else "what-if analysis"
                logger.info(f"Cleaning answer to remove {analysis_type} sections if present")
                # Remove common error analysis section headers and content if present
                original_answer = answer
                
                # Extract just the direct answer part (before any ERROR ANALYSIS sections)
                lines = answer.split('\n')
                cleaned_lines = []
                in_error_analysis_section = False
                
                for line in lines:
                    line_stripped = line.strip()
                    line_upper = line_stripped.upper()
                    
                    # Detect start of analysis sections (error analysis or what-if)
                    if any(header in line_upper for header in ['ERROR ANALYSIS', 'WHAT-IF ANALYSIS', 'WHAT IF ANALYSIS', 'PRIMARY AFFECTED SERVICE', 'DEPENDENT SERVICES', 'AFFECTED CONNECTIONS', 'BLAST RADIUS', 'RISK HOTSPOTS', 'HOW TO FIX THE ERROR', 'HOW TO MITIGATE RISK']):
                        in_error_analysis_section = True
                        continue
                    
                    # Stop collecting if we hit another section header
                    if in_error_analysis_section and line_stripped == '':
                        continue
                    
                    # Skip lines that look like section headers
                    if line_stripped and (line_stripped.startswith('=') or line_upper.startswith('PRIMARY') or line_upper.startswith('DEPENDENT') or line_upper.startswith('AFFECTED') or line_upper.startswith('BLAST') or line_upper.startswith('RISK') or line_upper.startswith('HOW TO FIX') or line_upper.startswith('HOW TO MITIGATE')):
                        continue
                    
                    # Include lines that look like actual answers
                    if not in_error_analysis_section or (line_stripped and not line_upper.startswith('AGENT STOPPED')):
                        cleaned_lines.append(line)
                    else:
                        break
                
                # If we cleaned the answer, use it
                if cleaned_lines and len(cleaned_lines) < len(lines):
                    answer = '\n'.join(cleaned_lines).strip()
                    logger.info(f"Cleaned answer from {len(lines)} lines to {len(cleaned_lines)} lines")
                elif any(header in original_answer.upper() for header in ['ERROR ANALYSIS', 'WHAT-IF ANALYSIS', 'WHAT IF ANALYSIS', 'PRIMARY AFFECTED SERVICE', 'BLAST RADIUS', 'RISK HOTSPOTS']):
                    # If the answer still contains analysis sections, extract just the first few sentences
                    logger.warning("Answer still contains analysis sections, extracting direct answer")
                    # Try to extract just the first meaningful paragraph (before analysis sections)
                    parts = original_answer.split('ERROR ANALYSIS')
                    if len(parts) == 1:
                        parts = original_answer.split('WHAT-IF ANALYSIS')
                    if len(parts) == 1:
                        parts = original_answer.split('WHAT IF ANALYSIS')
                    if len(parts) > 1:
                        # Take everything before analysis section
                        answer = parts[0].strip()
                    else:
                        # Take first 3 lines or first paragraph
                        first_paragraph = original_answer.split('\n\n')[0] if '\n\n' in original_answer else '\n'.join(original_answer.split('\n')[0:3])
                        answer = first_paragraph.strip()
                    
                    # If answer is still too long or contains section headers, take just first 200 chars
                    if len(answer) > 500 or any(header in answer.upper() for header in ['PRIMARY AFFECTED', 'DEPENDENT SERVICES', 'AFFECTED CONNECTIONS', 'BLAST RADIUS', 'RISK HOTSPOTS']):
                        # Extract just the first sentence(s) that directly answer the question
                        sentences = answer.split('. ')
                        relevant_sentences = []
                        for sentence in sentences[:3]:  # Take first 3 sentences
                            if sentence.strip() and not any(header in sentence.upper() for header in ['ERROR ANALYSIS', 'WHAT-IF ANALYSIS', 'WHAT IF ANALYSIS', 'PRIMARY AFFECTED', 'DEPENDENT SERVICES', 'AFFECTED CONNECTIONS', 'BLAST RADIUS', 'RISK HOTSPOTS']):
                                relevant_sentences.append(sentence.strip())
                        if relevant_sentences:
                            answer = '. '.join(relevant_sentences)
                            if not answer.endswith('.'):
                                answer += '.'
            
            # Format the answer to fit in chat box
            try:
                answer = self._format_answer_for_chat(answer)
            except Exception as e:
                logger.warning(f"Error formatting answer, using unformatted: {e}")
                # Continue with unformatted answer if formatting fails
            
            # Clean text to remove emojis and extraneous characters
            clean_answer = clean_text_for_chat(answer)
            
            return clean_answer
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

