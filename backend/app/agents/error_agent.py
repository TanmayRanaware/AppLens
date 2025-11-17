"""Error analyzer agent"""
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from app.config import settings
from app.db.models import Service, Interaction, Repository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Set, Optional
import re
import logging
import asyncio
import uuid
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


class ErrorAgent:
    """Agent for analyzing error logs and identifying affected services"""
    
    def __init__(self, db_session: AsyncSession, mcp_client=None):
        self.db_session = db_session
        self.mcp_client = mcp_client
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )
        
        self.agent = Agent(
            role="Error Log Analyzer",
            goal="Analyze error logs to identify the service where error occurred, understand the error, and determine which other services are affected through HTTP calls or Kafka connections",
            backstory="You are an expert at analyzing system logs and tracing errors across microservice architectures. You understand HTTP calls, Kafka events, and service dependencies. You can identify service names, endpoints, and connection patterns from error logs.",
            verbose=True,
            llm=self.llm,
            allow_delegation=False,
        )
    
    async def analyze(self, log_text: str) -> Dict[str, Any]:
        """Analyze error log and return affected services with domino effects"""
        try:
            # Step 1: CrewAI analyzes the error log
            analysis_result = await self._analyze_error_with_crewai(log_text)
            
            # Step 2: Extract service name from analysis
            source_service_name = analysis_result.get("source_service")
            if not source_service_name:
                # Fallback: try to extract from log text
                service_names = self._extract_service_names(log_text)
                source_service_name = service_names[0] if service_names else None
            
            if not source_service_name:
                raw_reasoning = analysis_result.get("analysis", "Analysis completed but no service identified")
                clean_reasoning = clean_text_for_chat(raw_reasoning)
                logger.warning("Could not identify source service from error log")
                return {
                    "error": "Could not identify source service from error log",
                    "primary_node": None,
                    "source_node": None,
                    "primary_service_name": None,
                    "source_service_name": None,
                    "dependent_nodes": [],
                    "affected_nodes": [],
                    "dependent_service_names": [],
                    "affected_service_names": [],
                    "affected_edges": [],
                    "reasoning": clean_reasoning,
                }
            
            # Step 3: Find source service in database
            source_service = await self._find_service_by_name(source_service_name)
            if not source_service:
                raw_reasoning = analysis_result.get("analysis", "")
                clean_reasoning = clean_text_for_chat(raw_reasoning)
                
                # Get list of available services for helpful error message
                available_services_result = await self.db_session.execute(select(Service.name))
                available_services = [s[0] for s in available_services_result.all()]
                available_services_list = "\n".join([f"  - {name}" for name in available_services[:20]])  # Show first 20
                
                error_reasoning = f"""{clean_reasoning}

GRAPH VISUALIZATION

⚠️ SERVICE NOT FOUND IN DATABASE

The error analyzer identified '{source_service_name}' as the primary service, but this service was not found in your database.

To visualize the error impact:
1. Go to the Dashboard and add repositories containing '{source_service_name}'
2. Run a scan to populate services in the database
3. Try the error analyzer again

Available services in database ({len(available_services)} total):
{available_services_list if available_services else "  - No services found. Please run a scan first."}
{f"\n  ... and {len(available_services) - 20} more" if len(available_services) > 20 else ""}

HOW TO FIX THE ERROR

{analysis_result.get("debug_steps", "Review the error log and check service health endpoints")}
"""
                
                logger.warning(f"Service '{source_service_name}' not found in database. Available services: {available_services}")
                return {
                    "error": f"Service '{source_service_name}' not found in database",
                    "primary_node": None,
                    "source_node": None,
                    "primary_service_name": source_service_name,
                    "source_service_name": source_service_name,
                    "dependent_nodes": [],
                    "affected_nodes": [],
                    "dependent_service_names": [],
                    "affected_service_names": [],
                    "affected_edges": [],
                    "reasoning": clean_text_for_chat(error_reasoning),
                }
            
            source_service_id = str(source_service.id)
            logger.info(f"Found source service: {source_service_name} (ID: {source_service_id})")
            
            # Step 4: Find connections from database (services connected to primary service)
            # Find all services that depend on the primary service (where primary is the target)
            # These are services that CALL the primary service, so they will be affected if primary fails
            direct_connections = await self._find_connections_from_db(source_service_id)
            logger.info(f"Found {len(direct_connections)} direct connections from DB for {source_service_name}")
            if direct_connections:
                logger.info(f"Direct connections: {direct_connections}")
            
            # Step 5: If no connections found, scan GitHub repo using MCP
            if not direct_connections and self.mcp_client:
                logger.info(f"No connections found in DB for {source_service_name}, scanning GitHub repo...")
                repo_connections = await self._scan_repo_for_connections(source_service)
                if repo_connections:
                    direct_connections = repo_connections
                    logger.info(f"Found {len(repo_connections)} connections from repo scan")
            
            # Step 6: Find domino effects (services affected by directly affected services)
            domino_connections = await self._find_domino_effects(direct_connections, source_service_id)
            
            # Step 7: Build result structure
            # Primary service = source_service_id (BLUE)
            # Dependent services = services connected to primary (RED)
            dependent_service_ids = set()
            affected_edges = []  # Edges from primary to dependent services (RED)
            direct_dependent_services = {}  # {service_id: {type, url, topic, reason}}
            domino_dependent_services = {}  # {service_id: {type, url, topic, reason, via_service}}
            
            # Process direct connections - find services that depend on primary
            logger.info(f"Processing {len(direct_connections)} direct connections...")
            for conn in direct_connections:
                conn_source = str(conn["source_service_id"])
                conn_target = str(conn["target_service_id"])
                conn_type = conn.get("type", "HTTP")
                conn_url = conn.get("url", "")
                conn_topic = conn.get("topic", "")
                
                # Primary service is the target - services that CALL it are dependent/affected
                # Example: cart-service calls user-service (primary) -> cart-service is dependent
                if conn_target == source_service_id:
                    dependent_service_id = conn_source
                    dependent_service_ids.add(dependent_service_id)
                    # Edge from dependent service TO primary service
                    affected_edges.append({
                        "source": dependent_service_id,  # Dependent service (RED)
                        "target": source_service_id,  # Primary service (BLUE)
                        "type": conn_type,
                    })
                    direct_dependent_services[dependent_service_id] = {
                        "type": conn_type,
                        "url": conn_url,
                        "topic": conn_topic,
                        "reason": f"Calls {source_service_name} via {conn_type}" + 
                                 (f" (URL: {conn_url})" if conn_url else "") +
                                 (f" (Topic: {conn_topic})" if conn_topic else "")
                    }
                    logger.info(f"  Marked service {dependent_service_id} as dependent (calls primary {source_service_id})")
                
                # Primary service is the source - services it CALLS might also be affected if primary fails
                # Example: user-service (primary) calls payment-service -> payment-service is dependent
                elif conn_source == source_service_id:
                    dependent_service_id = conn_target
                    dependent_service_ids.add(dependent_service_id)
                    # Edge from primary service TO dependent service
                    affected_edges.append({
                        "source": source_service_id,  # Primary service (BLUE)
                        "target": dependent_service_id,  # Dependent service (RED)
                        "type": conn_type,
                    })
                    direct_dependent_services[dependent_service_id] = {
                        "type": conn_type,
                        "url": conn_url,
                        "topic": conn_topic,
                        "reason": f"Called by {source_service_name} via {conn_type}" + 
                                 (f" (URL: {conn_url})" if conn_url else "") +
                                 (f" (Topic: {conn_topic})" if conn_topic else "")
                    }
                    logger.info(f"  Marked service {dependent_service_id} as dependent (called by primary {source_service_id})")
            
            logger.info(f"Total dependent services after direct connections: {len(dependent_service_ids)}")
            
            # Process domino connections - services affected through dependent services
            for conn in domino_connections:
                try:
                    dependent_service_id = str(conn.get("target_service_id", ""))
                    source_id = str(conn.get("source_service_id", ""))
                    conn_type = conn.get("type", "HTTP")
                    conn_url = conn.get("url", "")
                    conn_topic = conn.get("topic", "")
                    
                    if dependent_service_id and source_id and dependent_service_id != source_service_id:
                        dependent_service_ids.add(dependent_service_id)
                        # Edge from source service TO dependent service (through cascade)
                        affected_edges.append({
                            "source": source_id,
                            "target": dependent_service_id,
                            "type": conn_type,
                        })
                        # Find the name of the service that connects to this one (for domino explanation)
                        via_service_name = "another service"
                        try:
                            via_result = await self.db_session.execute(
                                select(Service).where(Service.id == uuid.UUID(source_id))
                            )
                            via_service = via_result.scalar_one_or_none()
                            if via_service:
                                via_service_name = via_service.name
                        except:
                            pass
                        
                        domino_dependent_services[dependent_service_id] = {
                            "type": conn_type,
                            "url": conn_url,
                            "topic": conn_topic,
                            "via_service": via_service_name,
                            "reason": f"Affected via {via_service_name} (domino effect) - {conn_type}" + 
                                     (f" (URL: {conn_url})" if conn_url else "") +
                                     (f" (Topic: {conn_topic})" if conn_topic else "")
                        }
                except Exception as conn_error:
                    logger.warning(f"Error processing domino connection: {conn_error}, conn: {conn}")
                    continue
            
            # Get service names and build service ID to name mapping
            dependent_service_names = []
            service_id_to_name = {}
            # Add primary service to mapping
            service_id_to_name[source_service_id] = source_service_name
            if dependent_service_ids:
                # Convert string UUIDs to UUID objects
                try:
                    uuid_ids = [uuid.UUID(id) for id in dependent_service_ids]
                    result = await self.db_session.execute(
                        select(Service).where(Service.id.in_(uuid_ids))
                    )
                    services = result.scalars().all()
                    dependent_service_names = [s.name for s in services]
                    service_id_to_name.update({str(s.id): s.name for s in services})
                except (ValueError, TypeError) as e:
                    logger.error(f"Error converting service IDs to UUIDs: {e}, IDs: {dependent_service_ids}")
                    dependent_service_names = []
            
            # Helper function to format URLs for display (truncate if too long)
            def format_url(url: str, max_length: int = 45) -> str:
                """Format URL to fit in chat box"""
                if not url:
                    return ""
                # Extract path if it's a full URL
                if url.startswith('http://') or url.startswith('https://'):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    path = parsed.path
                    if path:
                        url = path
                
                # Handle template strings like {SERVICE_URL}/path/{variable}
                if '{' in url:
                    import re
                    # Extract path part after variable placeholders
                    # Example: {INVENTORY_SERVICE_URL}/inventory/{item.product_id}/reserve
                    # Result: /inventory/{item.product_id}/reserve
                    # Remove {VARIABLE} patterns at the start
                    url = re.sub(r'^\{[^}]+\}', '', url)
                    # If URL doesn't start with /, add it
                    if url and not url.startswith('/'):
                        url = '/' + url
                    # Simplify variable placeholders in path
                    # Replace {variable} with {...} for readability
                    url = re.sub(r'\{[^}]+\}', '{...}', url)
                
                # Truncate if too long
                if len(url) > max_length:
                    # Try to keep the beginning and end
                    if '/' in url:
                        parts = url.split('/')
                        if len(parts) > 2:
                            # Keep first and last part
                            return f"/{parts[1]}/.../{parts[-1]}"
                    return url[:max_length-3] + "..."
                return url
            
            # Build detailed proof section
            proof_section = ""
            if dependent_service_names:
                proof_section = "\nDETAILED PROOF OF DEPENDENT SERVICES\n\n"
                
                # Direct connections
                if direct_dependent_services:
                    proof_section += "Direct Dependencies (Immediate Impact):\n\n"
                    for service_id, details in direct_dependent_services.items():
                        service_name = service_id_to_name.get(service_id, f"Service {service_id[:8]}...")
                        proof_section += f"{service_name}\n"
                        proof_section += f"  - Connection Type: {details['type']}\n"
                        if details.get('url'):
                            formatted_url = format_url(details['url'])
                            proof_section += f"  - HTTP Endpoint: {formatted_url}\n"
                        if details.get('topic'):
                            proof_section += f"  - Kafka Topic: {details['topic']}\n"
                        if "Calls" in details['reason']:
                            proof_section += f"  - Impact: {service_name} calls {source_service_name}. If {source_service_name} fails, {service_name} cannot complete operations that depend on it.\n"
                        else:
                            proof_section += f"  - Impact: {service_name} is called by {source_service_name}. If {source_service_name} fails, {service_name} may not receive expected calls or events.\n"
                        proof_section += "\n"
                
                # Domino effects
                if domino_dependent_services:
                    proof_section += "Domino Effects (Cascading Impact):\n\n"
                    for service_id, details in domino_dependent_services.items():
                        service_name = service_id_to_name.get(service_id, f"Service {service_id[:8]}...")
                        via_service = details.get('via_service', 'another service')
                        proof_section += f"{service_name}\n"
                        proof_section += f"  - Connection Type: {details['type']}\n"
                        if details.get('url'):
                            formatted_url = format_url(details['url'])
                            proof_section += f"  - HTTP Endpoint: {formatted_url}\n"
                        if details.get('topic'):
                            proof_section += f"  - Kafka Topic: {details['topic']}\n"
                        proof_section += f"  - Affected Via: {via_service} (which depends on {source_service_name})\n"
                        proof_section += f"  - Impact: Since {via_service} is affected by {source_service_name}, {service_name} is also impacted through the dependency chain.\n"
                        proof_section += "\n"
            
            # Build connections list with service names (edges from primary to dependent)
            connections_list_formatted = ""
            if affected_edges:
                for edge in affected_edges[:15]:  # Show up to 15 connections
                    source_name = service_id_to_name.get(str(edge['source']), f"Service {str(edge['source'])[:8]}...")
                    target_name = service_id_to_name.get(str(edge['target']), f"Service {str(edge['target'])[:8]}...")
                    if edge['source'] == source_service_id:
                        source_name = source_service_name
                    if edge['target'] == source_service_id:
                        target_name = source_service_name
                    connections_list_formatted += f"  - {source_name} -> {target_name} ({edge.get('type', 'HTTP')})\n"
                if len(affected_edges) > 15:
                    connections_list_formatted += f"  - ... and {len(affected_edges) - 15} more connection(s)\n"
            
            # Build clean, non-duplicated reasoning
            # Extract error description from analysis
            raw_analysis = analysis_result.get("analysis", "Analysis completed")
            raw_debug_steps = analysis_result.get("debug_steps", "Review the error log and check service health endpoints")
            
            # Extract error description (first part of analysis before detailed sections)
            error_description = raw_analysis.split("\n\n")[0] if "\n\n" in raw_analysis else raw_analysis.split("\n")[0] if "\n" in raw_analysis else raw_analysis
            
            reasoning = f"""ERROR ANALYSIS

{error_description}

PRIMARY AFFECTED SERVICE (BLUE NODE):
{source_service_name} (Service ID: {source_service_id})

The error log identifies {source_service_name} as the primary service where the error occurred. This service is marked BLUE in the graph to indicate it is the source of the error.

DEPENDENT SERVICES (RED NODES):
Total: {len(dependent_service_names)} service(s) affected

Services:
{chr(10).join([f"  - {name}" for name in dependent_service_names]) if dependent_service_names else "  - None found - No services are directly or indirectly dependent on the primary service."}

Breakdown:
  - Direct dependencies: {len(direct_dependent_services)} service(s) - Services directly connected to {source_service_name}
  - Domino effects: {len(domino_dependent_services)} service(s) - Services affected through cascading dependencies

{"These services are marked RED because they depend on " + source_service_name + " and will be impacted if the error is not fixed." if dependent_service_names else "No services depend on " + source_service_name + ". The error is isolated to the primary service."}

AFFECTED CONNECTIONS (RED EDGES):
Total: {len(affected_edges)} connection(s) affected

{connections_list_formatted if connections_list_formatted else "  - No connections found - No service interactions are affected by this error."}

These edges connect the primary service to dependent services and are marked RED to show the blast radius of potential impact.

{proof_section if proof_section else ""}

HOW TO FIX THE ERROR

{raw_debug_steps}

Recommended Actions:
1. Review the error in {source_service_name} and identify the root cause
2. Check the health and logs of dependent services to assess current impact
3. Fix the error in {source_service_name} to prevent further cascading failures
4. Monitor dependent services after the fix to ensure they recover properly
5. Consider implementing circuit breakers or retry mechanisms for dependent services
"""
            
            # Clean text to remove emojis and extraneous characters
            clean_reasoning = clean_text_for_chat(reasoning)
            clean_analysis = clean_text_for_chat(raw_analysis)
            
            return {
                "primary_node": source_service_id,  # BLUE - primary affected service
                "primary_service_name": source_service_name,
                "source_node": source_service_id,  # Keep for backward compatibility
                "source_service_name": source_service_name,
                "affected_nodes": list(dependent_service_ids),  # RED - dependent services
                "affected_service_names": dependent_service_names,
                "dependent_nodes": list(dependent_service_ids),  # RED - dependent services
                "dependent_service_names": dependent_service_names,
                "affected_edges": affected_edges,  # RED - edges from primary to dependent
                "reasoning": clean_reasoning,
                "analysis": clean_analysis,
                "confidence": 0.8,
            }
        except Exception as e:
            logger.error(f"Error in analyze method: {e}", exc_info=True)
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Full traceback: {error_trace}")
            # Return error response with more details
            error_reasoning = f"An error occurred while analyzing the error log.\n\nError: {str(e)}\n\nPlease check the backend logs for full details."
            clean_error_reasoning = clean_text_for_chat(error_reasoning)
            
            return {
                "error": f"Error analyzing log: {str(e)}",
                "reasoning": clean_error_reasoning,
                "source_node": None,
                "affected_nodes": [],
                "affected_edges": [],
                "error_details": str(e),
            }
    
    async def _analyze_error_with_crewai(self, log_text: str) -> Dict[str, Any]:
        """Use CrewAI to analyze the error log"""
        task = Task(
            description=f"""
            Analyze the following error log and provide a detailed analysis:
            
            {log_text}
            
            From this error log, identify:
            1. What is the error? (Describe the error clearly)
            2. Why has it occurred? (Root cause analysis)
            3. Which service is the source of this error? (Service name where error occurred)
            4. How to debug it? (Step-by-step debugging approach)
            5. What endpoints or connections might be affected? (HTTP endpoints, Kafka topics mentioned)
            
            IMPORTANT: 
            - Extract the exact service name where the error occurred (e.g., "user-service", "order-service")
            - Identify any HTTP endpoints mentioned (e.g., "/users/{{user_id}}/validate")
            - Identify any Kafka topics mentioned
            - Do NOT list all services in the system, only those directly mentioned or connected in the log
            
            Format your response with clear sections.
            """,
            agent=self.agent,
        )
        
        try:
            # Run CrewAI in a thread pool to avoid blocking async event loop
            def run_crew():
                crew = Crew(
                    agents=[self.agent],
                    tasks=[task],
                    verbose=True,
                )
                return crew.kickoff()
            
            # Run in thread pool to avoid blocking async event loop
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result_crew = await loop.run_in_executor(executor, run_crew)
            
            analysis_text = str(result_crew) if result_crew else "Analysis completed."
            
            # Extract service name from analysis
            source_service = self._extract_service_from_analysis(analysis_text, log_text)
            
            # Extract debug steps
            debug_steps = self._extract_debug_steps(analysis_text)
            
            return {
                "analysis": analysis_text,
                "source_service": source_service,
                "debug_steps": debug_steps,
            }
        except Exception as e:
            logger.error(f"Error running CrewAI agent: {e}")
            # Fallback extraction
            service_names = self._extract_service_names(log_text)
            return {
                "analysis": f"Error analysis failed: {str(e)}. Extracted service names: {', '.join(service_names)}",
                "source_service": service_names[0] if service_names else None,
                "debug_steps": "Review error log and check service health",
            }
    
    async def _find_service_by_name(self, service_name: str) -> Optional[Service]:
        """Find service in database by name"""
        logger.info(f"Searching for service: '{service_name}'")
        
        # Try exact match first
        result = await self.db_session.execute(
            select(Service).where(Service.name == service_name)
        )
        service = result.scalar_one_or_none()
        
        if service:
            logger.info(f"Found exact match: {service.name} (ID: {service.id})")
            return service
        
        # Try case-insensitive exact match
        result = await self.db_session.execute(
            select(Service).where(Service.name.ilike(service_name))
        )
        service = result.scalar_one_or_none()
        
        if service:
            logger.info(f"Found case-insensitive match: {service.name} (ID: {service.id})")
            return service
        
        # Try partial match (e.g., "user-service" matches "applens-user-service")
        result = await self.db_session.execute(
            select(Service).where(Service.name.ilike(f"%{service_name}%"))
        )
        services = result.scalars().all()
        
        if services:
            # Prefer services that end with the service name (e.g., "applens-user-service" for "user-service")
            for s in services:
                if s.name.lower().endswith(service_name.lower()):
                    logger.info(f"Found partial match (ends with): {s.name} (ID: {s.id})")
                    return s
            # Otherwise return first match
            logger.info(f"Found partial match: {services[0].name} (ID: {services[0].id})")
            return services[0]
        
        logger.warning(f"Service '{service_name}' not found in database")
        return None
    
    async def _find_connections_from_db(self, source_service_id: str) -> List[Dict[str, Any]]:
        """Find all connections from source service in database"""
        connections = []
        try:
            source_service_id_uuid = uuid.UUID(source_service_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid UUID format for source_service_id: {source_service_id}, error: {e}")
            return []
        
        # Find HTTP/Kafka connections where source_service is the target (other services call it)
        # These are services that DEPEND on the source service (they will be affected)
        result = await self.db_session.execute(
            select(Interaction).where(Interaction.target_service_id == source_service_id_uuid)
        )
        interactions = result.scalars().all()
        logger.info(f"Found {len(interactions)} interactions where {source_service_id} is the TARGET (other services call it)")
        
        for interaction in interactions:
            conn = {
                "source_service_id": str(interaction.source_service_id),
                "target_service_id": str(interaction.target_service_id),
                "type": interaction.edge_type.value,
                "url": interaction.http_url,
                "topic": interaction.kafka_topic,
            }
            connections.append(conn)
            logger.info(f"  Connection: Service {interaction.source_service_id} -> {interaction.target_service_id} ({interaction.edge_type.value})")
        
        # Find HTTP/Kafka connections where source_service is the source (it calls other services)
        # These are services that the source service DEPENDS on (they might be affected if source fails)
        result = await self.db_session.execute(
            select(Interaction).where(Interaction.source_service_id == source_service_id_uuid)
        )
        interactions = result.scalars().all()
        logger.info(f"Found {len(interactions)} interactions where {source_service_id} is the SOURCE (it calls other services)")
        
        for interaction in interactions:
            conn = {
                "source_service_id": str(interaction.source_service_id),
                "target_service_id": str(interaction.target_service_id),
                "type": interaction.edge_type.value,
                "url": interaction.http_url,
                "topic": interaction.kafka_topic,
            }
            connections.append(conn)
            logger.info(f"  Connection: Service {interaction.source_service_id} -> {interaction.target_service_id} ({interaction.edge_type.value})")
        
        logger.info(f"Total connections found: {len(connections)}")
        return connections
    
    async def _scan_repo_for_connections(self, source_service: Service) -> List[Dict[str, Any]]:
        """Scan GitHub repo using MCP to find connections if not in DB"""
        if not self.mcp_client or not source_service.repo_id:
            return []
        
        try:
            # Get repository
            result = await self.db_session.execute(
                select(Repository).where(Repository.id == source_service.repo_id)
            )
            repo = result.scalar_one_or_none()
            if not repo:
                return []
            
            # Use MCP to get code files (similar to scan_pipeline)
            logger.info(f"Scanning repo {repo.full_name} for connections...")
            
            # Import detectors
            from app.services.code_fetch import CodeFetchService
            from app.services.detectors.http_python import PythonHTTPDetector
            from app.services.detectors.kafka_python import PythonKafkaDetector
            
            # Fetch code files
            code_fetch = CodeFetchService(self.mcp_client)
            files = await code_fetch.fetch_repo_files(repo.full_name, "main")
            
            # Run detectors
            http_detector = PythonHTTPDetector()
            kafka_detector = PythonKafkaDetector()
            
            connections = []
            for file_info in files:
                file_path = file_info["path"]
                content = file_info["content"]
                
                # Detect HTTP calls
                http_findings = http_detector.detect(file_path, content)
                for finding in http_findings:
                    # Extract target service from URL
                    url = finding.get("url", "")
                    # Try to find target service in DB
                    # This is simplified - you'd need to match URL to service
                    pass
                
                # Detect Kafka topics
                kafka_findings = kafka_detector.detect(file_path, content)
                for finding in kafka_findings:
                    topic = finding.get("topic", "")
                    # Try to find consumer service in DB
                    result = await self.db_session.execute(
                        select(Interaction).where(Interaction.kafka_topic == topic)
                    )
                    interactions = result.scalars().all()
                    for interaction in interactions:
                        if str(interaction.source_service_id) != str(source_service.id):
                            connections.append({
                                "source_service_id": str(source_service.id),
                                "target_service_id": str(interaction.target_service_id),
                                "type": "Kafka",
                                "topic": topic,
                            })
            
            return connections
        except Exception as e:
            logger.error(f"Error scanning repo: {e}")
            return []
    
    async def _find_domino_effects(
        self, 
        direct_connections: List[Dict[str, Any]], 
        source_service_id: str
    ) -> List[Dict[str, Any]]:
        """Find domino effects: services affected by directly affected services"""
        domino_connections = []
        visited_services = {source_service_id}
        
        # Get directly affected service IDs (both source and target, excluding the source_service_id itself)
        directly_affected_ids = set()
        for conn in direct_connections:
            conn_source = str(conn.get("source_service_id", ""))
            conn_target = str(conn.get("target_service_id", ""))
            if conn_source and conn_source != source_service_id:
                directly_affected_ids.add(conn_source)
            if conn_target and conn_target != source_service_id:
                directly_affected_ids.add(conn_target)
        visited_services.update(directly_affected_ids)
        
        # For each directly affected service, find its connections
        for affected_id in directly_affected_ids:
            try:
                affected_id_uuid = uuid.UUID(affected_id)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid UUID format for affected_id: {affected_id}, error: {e}, skipping")
                continue
            
            # Find connections where this service is the source (it calls other services)
            result = await self.db_session.execute(
                select(Interaction).where(Interaction.source_service_id == affected_id_uuid)
            )
            interactions = result.scalars().all()
            
            for interaction in interactions:
                target_id = str(interaction.target_service_id)
                # Only add if not already visited (avoid cycles)
                if target_id not in visited_services:
                    domino_connections.append({
                        "source_service_id": str(interaction.source_service_id),
                        "target_service_id": str(interaction.target_service_id),
                        "type": interaction.edge_type.value,
                        "url": interaction.http_url,
                        "topic": interaction.kafka_topic,
                    })
                    visited_services.add(target_id)
        
        return domino_connections
    
    def _extract_service_from_analysis(self, analysis_text: str, log_text: str) -> Optional[str]:
        """Extract service name from CrewAI analysis or log text"""
        # Try to extract from analysis text with improved patterns
        patterns = [
            r'source of this error is (?:the\s+)?[\'"]([a-z-]+(?:-service)?)[\'"]',
            r'source service[:\s]+(?:is\s+)?[\'"]?([a-z-]+(?:-service)?)[\'"]?',
            r'source service is (?:the\s+)?[\'"]?([a-z-]+(?:-service)?)[\'"]?',
            r'service[:\s]+(?:is\s+)?[\'"]?([a-z-]+(?:-service)?)[\'"]?',
            r'error occurred in[:\s]+(?:the\s+)?[\'"]?([a-z-]+(?:-service)?)[\'"]?',
            r'source[:\s]+([a-z-]+(?:-service)?)',
            # Pattern to match "user-service" or "user_service" in quotes or after "is"
            r'(?:is|are|the)\s+[\'"]?([a-z]+(?:[-_][a-z]+)*(?:-service|_service))[\'"]?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis_text, re.IGNORECASE)
            if match:
                service_name = match.group(1)
                logger.info(f"Extracted service name from analysis: {service_name}")
                return service_name
        
        logger.warning(f"Could not extract service name from analysis text. Trying log text extraction...")
        # Fallback to log text extraction
        service_names = self._extract_service_names(log_text)
        if service_names:
            logger.info(f"Extracted service name from log text: {service_names[0]}")
            return service_names[0]
        
        logger.error(f"Could not extract service name from either analysis or log text")
        return None
    
    def _extract_debug_steps(self, analysis_text: str) -> str:
        """Extract debugging steps from analysis"""
        # Look for "How to debug" or "Debugging" section
        debug_match = re.search(r'(?:how to debug|debugging|debug steps?)[:\s]+(.+?)(?:\n\n|\n##|$)', analysis_text, re.IGNORECASE | re.DOTALL)
        if debug_match:
            return debug_match.group(1).strip()
        return "Review the error log and check service health endpoints"
    
    def _extract_service_names(self, log_text: str) -> List[str]:
        """Extract service names from log text"""
        patterns = [
            r'([a-z]+(?:-[a-z]+)+-service)',
            r'([a-z]+_service)',
            r'(service[:\s]+([a-z-]+))',
            r'ERROR\s+([a-z-]+(?:-service)?)',
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
        return matches[:10]
    
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
