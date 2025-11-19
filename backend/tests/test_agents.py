"""Unit tests for AI agents"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.agents.error_agent import ErrorAgent
from app.agents.whatif_agent import WhatIfAgent
from app.agents.nlq_agent import NLQAgent
from app.agents.graph_agent import GraphAgent
from app.db.models import Service, Interaction, EdgeType, Repository


class TestErrorAgent:
    """Test suite for ErrorAgent"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client"""
        return Mock()
    
    @pytest.fixture
    def error_agent(self, mock_db_session, mock_mcp_client):
        """Create ErrorAgent instance with mocked dependencies"""
        with patch('app.agents.error_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            agent = ErrorAgent(mock_db_session, mock_mcp_client)
            return agent
    
    def test_init(self, mock_db_session, mock_mcp_client):
        """Test ErrorAgent initialization"""
        with patch('app.agents.error_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            with patch('app.agents.error_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                agent = ErrorAgent(mock_db_session, mock_mcp_client)
                
                assert agent.db_session == mock_db_session
                assert agent.mcp_client == mock_mcp_client
                assert agent.llm == mock_llm_instance
                assert agent.agent == mock_agent
    
    @pytest.mark.asyncio
    async def test_extract_service_names(self, error_agent):
        """Test service name extraction from log text"""
        log_text = """
        ERROR in user-service: Connection timeout
        ERROR order-service: Database connection failed
        payment-service: Invalid request
        ERROR inventory-service
        """
        
        service_names = error_agent._extract_service_names(log_text)
        
        assert "user-service" in service_names
        assert "order-service" in service_names
        assert "payment-service" in service_names
        assert "inventory-service" in service_names
    
    @pytest.mark.asyncio
    async def test_extract_service_names_patterns(self, error_agent):
        """Test various service name patterns"""
        test_cases = [
            ("user-service: error", ["user-service"]),
            ("auth_service: failed", ["auth_service"]),
            ("ERROR payment-service", ["payment-service"]),
            ("checkout-service logs", ["checkout-service"]),
        ]
        
        for log_text, expected in test_cases:
            result = error_agent._extract_service_names(log_text)
            assert all(name in result for name in expected)
    
    @pytest.mark.asyncio
    async def test_extract_urls(self, error_agent):
        """Test URL extraction from log text"""
        log_text = """
        Failed to connect to https://api.example.com/v1/users
        HTTP GET /api/payments/status failed
        POST https://auth-service.internal/login
        """
        
        urls = error_agent._extract_urls(log_text)
        
        assert "https://api.example.com/v1/users" in urls
        assert "/api/payments/status" in urls
        assert "https://auth-service.internal/login" in urls
    
    @pytest.mark.asyncio
    async def test_extract_kafka_topics(self, error_agent):
        """Test Kafka topic extraction"""
        log_text = """
        Kafka topic: user-events
        Failed to consume from kafka:payment-topic
        topic order-updates is down
        """
        
        topics = error_agent._extract_kafka_topics(log_text)
        
        assert "user-events" in topics
        assert "payment-topic" in topics
        assert "order-updates" in topics
    
    @pytest.mark.asyncio
    async def test_extract_debug_steps(self, error_agent):
        """Test debug steps extraction from analysis"""
        analysis_text = """
        The error occurred due to connection timeout.
        
        How to debug:
        1. Check network connectivity
        2. Verify service health
        3. Review logs
        """
        
        debug_steps = error_agent._extract_debug_steps(analysis_text)
        
        assert "Check network connectivity" in debug_steps
        assert "Verify service health" in debug_steps
        assert "Review logs" in debug_steps
    
    @pytest.mark.asyncio
    async def test_extract_debug_steps_no_section(self, error_agent):
        """Test debug steps extraction when no section exists"""
        analysis_text = "The error occurred due to connection timeout."
        
        debug_steps = error_agent._extract_debug_steps(analysis_text)
        
        assert "Review the error log and check service health endpoints" == debug_steps
    
    @pytest.mark.asyncio
    async def test_extract_service_from_analysis(self, error_agent):
        """Test service name extraction from AI analysis"""
        analysis_text = 'The source of this error is "user-service" in the authentication flow.'
        
        with patch('app.agents.error_agent.logger'):
            service_name = error_agent._extract_service_from_analysis(analysis_text, "")
            assert service_name == "user-service"
    
    @pytest.mark.asyncio
    async def test_extract_service_from_analysis_fallback(self, error_agent):
        """Test service extraction fallback to log text"""
        analysis_text = "No service mentioned here."
        log_text = "ERROR in payment-service"
        
        with patch('app.agents.error_agent.logger'):
            service_name = error_agent._extract_service_from_analysis(analysis_text, log_text)
            assert service_name == "payment-service"
    
    @pytest.mark.asyncio
    async def test_find_service_by_name_exact_match(self, error_agent, mock_db_session):
        """Test finding service with exact name match"""
        mock_service = Mock()
        mock_service.id = uuid.uuid4()
        mock_service.name = "user-service"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_service
        mock_db_session.execute.return_value = mock_result
        
        with patch('app.agents.error_agent.logger'):
            result = await error_agent._find_service_by_name("user-service")
            assert result == mock_service
    
    @pytest.mark.asyncio
    async def test_find_service_by_name_case_insensitive(self, error_agent, mock_db_session):
        """Test finding service with case-insensitive match"""
        mock_service = Mock()
        mock_service.id = uuid.uuid4()
        mock_service.name = "User-Service"
        
        # First call returns None (exact match failed)
        # Second call returns service (case-insensitive match)
        mock_results = [AsyncMock(), AsyncMock()]
        mock_results[0].scalar_one_or_none.return_value = None
        mock_results[1].scalar_one_or_none.return_value = mock_service
        mock_db_session.execute.side_effect = mock_results
        
        with patch('app.agents.error_agent.logger'):
            result = await error_agent._find_service_by_name("user-service")
            assert result == mock_service
    
    @pytest.mark.asyncio
    async def test_find_service_by_name_partial_match(self, error_agent, mock_db_session):
        """Test finding service with partial match"""
        mock_service = Mock()
        mock_service.id = uuid.uuid4()
        mock_service.name = "applens-user-service"
        
        # First two calls return None
        # Third call returns partial match
        mock_results = [AsyncMock(), AsyncMock(), AsyncMock()]
        mock_results[0].scalar_one_or_none.return_value = None
        mock_results[1].scalar_one_or_none.return_value = None
        mock_results[2].scalars.return_value.all.return_value = [mock_service]
        mock_db_session.execute.side_effect = mock_results
        
        with patch('app.agents.error_agent.logger'):
            result = await error_agent._find_service_by_name("user-service")
            assert result == mock_service
    
    @pytest.mark.asyncio
    async def test_find_service_by_name_not_found(self, error_agent, mock_db_session):
        """Test service not found"""
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        with patch('app.agents.error_agent.logger'):
            result = await error_agent._find_service_by_name("nonexistent-service")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_find_connections_from_db(self, error_agent, mock_db_session):
        """Test finding connections from database"""
        source_service_id = str(uuid.uuid4())
        
        mock_interaction = Mock()
        mock_interaction.source_service_id = uuid.uuid4()
        mock_interaction.target_service_id = uuid.UUID(source_service_id)
        mock_interaction.edge_type = EdgeType.HTTP
        mock_interaction.http_url = "/api/test"
        mock_interaction.kafka_topic = None
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_interaction]
        mock_db_session.execute.return_value = mock_result
        
        connections = await error_agent._find_connections_from_db(source_service_id)
        
        assert len(connections) == 1
        assert connections[0]["target_service_id"] == source_service_id
        assert connections[0]["type"] == "HTTP"
        assert connections[0]["url"] == "/api/test"
    
    @pytest.mark.asyncio
    async def test_find_connections_from_db_invalid_uuid(self, error_agent):
        """Test connection search with invalid UUID"""
        connections = await error_agent._find_connections_from_db("invalid-uuid")
        assert connections == []
    
    @pytest.mark.asyncio
    async def test_analyze_error_log_success(self, error_agent, mock_db_session):
        """Test successful error log analysis"""
        # Mock the analysis result
        mock_analysis = {
            "analysis": "Error occurred in user-service",
            "source_service": "user-service",
            "debug_steps": "Check service health"
        }
        
        # Mock finding service
        mock_service = Mock()
        mock_service.id = uuid.uuid4()
        mock_service.name = "user-service"
        
        # Mock finding connections
        mock_interaction = Mock()
        mock_interaction.source_service_id = uuid.uuid4()
        mock_interaction.target_service_id = mock_service.id
        mock_interaction.edge_type = EdgeType.HTTP
        mock_interaction.http_url = "/api/test"
        mock_interaction.kafka_topic = None
        
        # Setup mocks
        with patch.object(error_agent, '_analyze_error_with_crewai', return_value=mock_analysis):
            with patch.object(error_agent, '_find_service_by_name', return_value=mock_service):
                with patch.object(error_agent, '_find_connections_from_db', return_value=[]):
                    with patch.object(error_agent, '_find_domino_effects', return_value=[]):
                        result = await error_agent.analyze("Error in user-service")
                        
                        assert "source_node" in result
                        assert "affected_nodes" in result
                        assert "reasoning" in result
                        assert result["source_node"] == str(mock_service.id)
    
    @pytest.mark.asyncio
    async def test_analyze_error_log_no_service_identified(self, error_agent):
        """Test error analysis when no service can be identified"""
        mock_analysis = {
            "analysis": "Generic error occurred",
            "source_service": None,
            "debug_steps": "Check logs"
        }
        
        with patch.object(error_agent, '_analyze_error_with_crewai', return_value=mock_analysis):
            result = await error_agent.analyze("Generic error")
            
            assert "error" in result
            assert "Could not identify source service" in result["error"]
    
    @pytest.mark.asyncio
    async def test_analyze_error_log_service_not_found(self, error_agent, mock_db_session):
        """Test error analysis when identified service is not in database"""
        mock_analysis = {
            "analysis": "Error in unknown-service",
            "source_service": "unknown-service",
            "debug_steps": "Check logs"
        }
        
        with patch.object(error_agent, '_analyze_error_with_crewai', return_value=mock_analysis):
            with patch.object(error_agent, '_find_service_by_name', return_value=None):
                result = await error_agent.analyze("Error in unknown-service")
                
                assert "error" in result
                assert "Service 'unknown-service' not found in database" in result["error"]


class TestWhatIfAgent:
    """Test suite for WhatIfAgent"""
    
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def whatif_agent(self, mock_db_session):
        with patch('app.agents.whatif_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            with patch('app.agents.whatif_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                agent = WhatIfAgent(mock_db_session)
                return agent
    
    def test_init(self, mock_db_session):
        """Test WhatIfAgent initialization"""
        with patch('app.agents.whatif_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            with patch('app.agents.whatif_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                agent = WhatIfAgent(mock_db_session)
                assert agent.db_session == mock_db_session
    
    @pytest.mark.asyncio
    async def test_simulate_change_analysis(self, whatif_agent, mock_db_session):
        """Test change impact simulation"""
        # Mock the analysis
        with patch.object(whatif_agent, '_analyze_change_with_crewai') as mock_analyze:
            mock_analyze.return_value = {
                "analysis": "Change will affect payment-service",
                "changed_services": ["payment-service"],
                "impact_assessment": "High impact on downstream services"
            }
            
            result = await whatif_agent.simulate(
                change_description="Update payment API endpoint",
                repo="owner/repo",
                file_path="src/payment/api.py",
                diff="Changed endpoint from /v1 to /v2"
            )
            
            assert "changed_service_ids" in result
            assert "reasoning" in result


class TestNLQAgent:
    """Test suite for NLQAgent"""
    
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def nlq_agent(self, mock_db_session):
        with patch('app.agents.nlq_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            with patch('app.agents.nlq_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                agent = NLQAgent(mock_db_session)
                return agent
    
    def test_init(self, mock_db_session):
        """Test NLQAgent initialization"""
        with patch('app.agents.nlq_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            with patch('app.agents.nlq_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                agent = NLQAgent(mock_db_session)
                assert agent.db_session == mock_db_session
    
    @pytest.mark.asyncio
    async def test_process_services_query(self, nlq_agent, mock_db_session):
        """Test processing services-related queries"""
        with patch.object(nlq_agent, '_query_service_calls') as mock_query:
            mock_query.return_value = {"services": ["user-service", "auth-service"]}
            
            result = await nlq_agent.query("Which services call auth-service?")
            
            assert "results" in result
            assert "graph_hints" in result
    
    @pytest.mark.asyncio
    async def test_process_kafka_query(self, nlq_agent, mock_db_session):
        """Test processing Kafka-related queries"""
        with patch.object(nlq_agent, '_query_kafka_topics') as mock_query:
            mock_query.return_value = {"topics": ["user-events", "order-events"]}
            
            result = await nlq_agent.query("Show me Kafka topics")
            
            assert "results" in result
            assert "graph_hints" in result
    
    @pytest.mark.asyncio
    async def test_process_generic_query(self, nlq_agent, mock_db_session):
        """Test processing generic queries"""
        with patch.object(nlq_agent, '_generic_query') as mock_query:
            mock_query.return_value = {"answer": "General system information"}
            
            result = await nlq_agent.query("What is the system status?")
            
            assert "results" in result
            assert result["results"]["answer"] == "General system information"


class TestGraphAgent:
    """Test suite for GraphAgent"""
    
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def graph_agent(self, mock_db_session):
        agent = GraphAgent(mock_db_session)
        return agent
    
    def test_init(self, mock_db_session):
        """Test GraphAgent initialization"""
        agent = GraphAgent(mock_db_session)
        assert agent.db_session == mock_db_session
    
    @pytest.mark.asyncio
    async def test_build_graph_data(self, graph_agent, mock_db_session):
        """Test graph data building"""
        # Mock database responses
        mock_services = [
            Mock(id=uuid.uuid4(), name="service-a", repo_id=None, language="python"),
            Mock(id=uuid.uuid4(), name="service-b", repo_id=None, language="java"),
        ]
        
        mock_interactions = [
            Mock(
                source_service_id=mock_services[0].id,
                target_service_id=mock_services[1].id,
                edge_type=EdgeType.HTTP,
                http_method="GET",
                http_url="/api/test"
            ),
        ]
        
        # Setup mock responses
        services_result = AsyncMock()
        services_result.scalars.return_value.all.return_value = mock_services
        
        interactions_result = AsyncMock()
        interactions_result.scalars.return_value.all.return_value = mock_interactions
        
        mock_db_session.execute.side_effect = [services_result, interactions_result]
        
        result = await graph_agent.build_graph_data()
        
        assert "nodes" in result
        assert "links" in result
        assert len(result["nodes"]) == 2
        assert len(result["links"]) == 1