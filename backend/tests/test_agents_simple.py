"""Simplified unit tests for AI agents"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import uuid

from app.agents.error_agent import ErrorAgent
from app.agents.nlq_agent import NLQAgent
from app.db.models import Service, Interaction, EdgeType


class TestErrorAgent:
    """Test suite for ErrorAgent"""
    
    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def error_agent(self, mock_db_session):
        with patch('app.agents.error_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            with patch('app.agents.error_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                agent = ErrorAgent(mock_db_session)
                return agent
    
    def test_init(self, mock_db_session):
        with patch('app.agents.error_agent.ChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            with patch('app.agents.error_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                
                agent = ErrorAgent(mock_db_session)
                assert agent.db_session == mock_db_session
    
    @pytest.mark.asyncio
    async def test_extract_service_names(self, error_agent):
        log_text = "ERROR in user-service: Connection timeout"
        service_names = error_agent._extract_service_names(log_text)
        assert "user-service" in service_names
    
    @pytest.mark.asyncio
    async def test_extract_urls(self, error_agent):
        log_text = "Failed to connect to https://api.example.com/v1/users"
        urls = error_agent._extract_urls(log_text)
        assert "https://api.example.com/v1/users" in urls
    
    @pytest.mark.asyncio
    async def test_analyze_error_log_success(self, error_agent, mock_db_session):
        mock_analysis = {
            "analysis": "Error occurred in user-service",
            "source_service": "user-service",
            "debug_steps": "Check service health"
        }
        
        mock_service = Mock()
        mock_service.id = uuid.uuid4()
        mock_service.name = "user-service"
        
        with patch.object(error_agent, '_analyze_error_with_crewai', return_value=mock_analysis):
            with patch.object(error_agent, '_find_service_by_name', return_value=mock_service):
                with patch.object(error_agent, '_find_connections_from_db', return_value=[]):
                    with patch.object(error_agent, '_find_domino_effects', return_value=[]):
                        result = await error_agent.analyze("Error in user-service")
                        
                        assert "source_node" in result
                        assert "affected_nodes" in result
                        assert "reasoning" in result


class TestNLQAgent:
    """Test suite for NLQAgent"""
    
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock()
    
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
        with patch.object(nlq_agent, '_query_service_calls') as mock_query:
            mock_query.return_value = {"services": ["user-service", "auth-service"]}
            
            result = await nlq_agent.query("Which services call auth-service?")
            
            assert "results" in result
            assert "graph_hints" in result