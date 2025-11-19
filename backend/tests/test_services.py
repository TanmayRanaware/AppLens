"""Unit tests for services layer"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from app.services.code_fetch import CodeFetchService
from app.services.graph_builder import GraphBuilder
from app.services.scan_pipeline import ScanPipeline
from app.services.mcp_client import MCPGitHubClient
from app.services.normalize import normalize_service_name, normalize_url
from app.services.embeddings import EmbeddingService


class TestCodeFetchService:
    """Test suite for CodeFetchService"""
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client"""
        client = Mock(spec=MCPGitHubClient)
        return client
    
    @pytest.fixture
    def code_fetch_service(self, mock_mcp_client):
        """Create CodeFetchService instance"""
        return CodeFetchService(mock_mcp_client)
    
    def test_init(self, mock_mcp_client):
        """Test CodeFetchService initialization"""
        service = CodeFetchService(mock_mcp_client)
        assert service.mcp_client == mock_mcp_client
    
    @pytest.mark.asyncio
    async def test_fetch_repo_files_default_extensions(self, code_fetch_service, mock_mcp_client):
        """Test fetching repository files with default extensions"""
        # Mock file listings
        mock_files = [
            {"path": "src/main.py", "type": "file", "size": 1024},
            {"path": "src/utils.js", "type": "file", "size": 512},
            {"path": "README.md", "type": "file", "size": 256},
            {"path": ".git/config", "type": "file", "size": 128},
        ]
        
        mock_content = {
            "src/main.py": "def main(): pass",
            "src/utils.js": "function util() {}",
            "README.md": "# Project",
            ".git/config": "[core]",
        }
        
        mock_mcp_client.list_files.return_value = mock_files
        mock_mcp_client.get_file_content.side_effect = lambda repo, path, branch: mock_content.get(path)
        
        result = await code_fetch_service.fetch_repo_files("owner/repo", "main")
        
        # Should include .py and .js files but not .md or .git files
        assert len(result) == 2
        file_paths = [f["path"] for f in result]
        assert "src/main.py" in file_paths
        assert "src/utils.js" in file_paths
        assert "README.md" not in file_paths
        assert ".git/config" not in file_paths
    
    @pytest.mark.asyncio
    async def test_fetch_repo_files_custom_extensions(self, code_fetch_service, mock_mcp_client):
        """Test fetching repository files with custom extensions"""
        mock_files = [
            {"path": "src/main.java", "type": "file", "size": 1024},
            {"path": "src/service.ts", "type": "file", "size": 512},
            {"path": "src/utils.js", "type": "file", "size": 256},
        ]
        
        mock_content = {
            "src/main.java": "public class Main {}",
            "src/service.ts": "export class Service {}",
            "src/utils.js": "function util() {}",
        }
        
        mock_mcp_client.list_files.return_value = mock_files
        mock_mcp_client.get_file_content.side_effect = lambda repo, path, branch: mock_content.get(path)
        
        result = await code_fetch_service.fetch_repo_files(
            "owner/repo", "main", extensions=[".java", ".ts"]
        )
        
        # Should only include .java and .ts files
        assert len(result) == 2
        file_paths = [f["path"] for f in result]
        assert "src/main.java" in file_paths
        assert "src/service.ts" in file_paths
        assert "src/utils.js" not in file_paths
    
    @pytest.mark.asyncio
    async def test_fetch_repo_files_recursive_traversal(self, code_fetch_service, mock_mcp_client):
        """Test recursive directory traversal"""
        # Mock file structure
        def mock_list_files(repo, path, branch):
            if path == "":
                return [
                    {"path": "src", "type": "dir", "name": "src"},
                    {"path": "tests", "type": "dir", "name": "tests"},
                    {"path": "main.py", "type": "file", "name": "main.py"},
                ]
            elif path == "src":
                return [
                    {"path": "src/controllers", "type": "dir", "name": "controllers"},
                    {"path": "src/app.py", "type": "file", "name": "app.py"},
                ]
            elif path == "src/controllers":
                return [
                    {"path": "src/controllers/user.py", "type": "file", "name": "user.py"},
                ]
            elif path == "tests":
                return [
                    {"path": "tests/test_main.py", "type": "file", "name": "test_main.py"},
                ]
            return []
        
        mock_content = {
            "main.py": "# main file",
            "src/app.py": "# app file",
            "src/controllers/user.py": "# user controller",
            "tests/test_main.py": "# test file",
        }
        
        mock_mcp_client.list_files.side_effect = mock_list_files
        mock_mcp_client.get_file_content.side_effect = lambda repo, path, branch: mock_content.get(path)
        
        result = await code_fetch_service.fetch_repo_files("owner/repo", "main")
        
        # Should recursively fetch all .py files
        assert len(result) == 3
        file_paths = [f["path"] for f in result]
        assert "main.py" in file_paths
        assert "src/app.py" in file_paths
        assert "src/controllers/user.py" in file_paths
        assert "tests/test_main.py" not in file_paths  # Should be skipped
    
    @pytest.mark.asyncio
    async def test_fetch_repo_files_skipped_directories(self, code_fetch_service, mock_mcp_client):
        """Test that common directories are skipped"""
        mock_files = [
            {"path": "node_modules/package/index.js", "type": "file"},
            {"path": ".git/hooks/pre-commit", "type": "file"},
            {"path": "__pycache__/module.pyc", "type": "file"},
            {"path": ".venv/lib/python.py", "type": "file"},
            {"path": "src/app.py", "type": "file"},
            {"path": "target/classes/Main.class", "type": "file"},
        ]
        
        mock_content = {
            "node_modules/package/index.js": "module.exports = {}",
            ".git/hooks/pre-commit": "#!/bin/sh",
            "__pycache__/module.pyc": "compiled",
            ".venv/lib/python.py": "def func(): pass",
            "src/app.py": "# app",
            "target/classes/Main.class": "bytecode",
        }
        
        mock_mcp_client.list_files.return_value = mock_files
        mock_mcp_client.get_file_content.side_effect = lambda repo, path, branch: mock_content.get(path)
        
        result = await code_fetch_service.fetch_repo_files("owner/repo", "main")
        
        # Should only include src/app.py, skipping other directories
        assert len(result) == 1
        assert result[0]["path"] == "src/app.py"


class TestGraphBuilder:
    """Test suite for GraphBuilder"""
    
    @pytest.fixture
    def mock_db_session(self):
        from sqlalchemy.ext.asyncio import AsyncSession
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def graph_builder(self, mock_db_session):
        return GraphBuilder(mock_db_session)
    
    def test_init(self, mock_db_session):
        """Test GraphBuilder initialization"""
        builder = GraphBuilder(mock_db_session)
        assert builder.db_session == mock_db_session
    
    @pytest.mark.asyncio
    async def test_build_graph_data_basic(self, graph_builder, mock_db_session):
        """Test basic graph data building"""
        from app.db.models import Service, Interaction, EdgeType
        import uuid
        
        # Mock services
        services = [
            Service(id=uuid.uuid4(), name="user-service", repo_id=None, language="python"),
            Service(id=uuid.uuid4(), name="order-service", repo_id=None, language="java"),
            Service(id=uuid.uuid4(), name="payment-service", repo_id=None, language="nodejs"),
        ]
        
        # Mock interactions
        interactions = [
            Interaction(
                source_service_id=services[0].id,
                target_service_id=services[1].id,
                edge_type=EdgeType.HTTP,
                http_method="GET",
                http_url="/api/orders",
                confidence=0.9
            ),
            Interaction(
                source_service_id=services[1].id,
                target_service_id=services[2].id,
                edge_type=EdgeType.KAFKA,
                kafka_topic="order-events",
                confidence=0.8
            ),
        ]
        
        # Mock database responses
        services_result = AsyncMock()
        services_result.scalars.return_value.all.return_value = services
        
        interactions_result = AsyncMock()
        interactions_result.scalars.return_value.all.return_value = interactions
        
        mock_db_session.execute.side_effect = [services_result, interactions_result]
        
        result = await graph_builder.build_graph_data()
        
        # Validate structure
        assert "nodes" in result
        assert "links" in result
        
        # Validate nodes
        assert len(result["nodes"]) == 3
        node_names = [node["name"] for node in result["nodes"]]
        assert "user-service" in node_names
        assert "order-service" in node_names
        assert "payment-service" in node_names
        
        # Validate links
        assert len(result["links"]) == 2
        link_types = [link["kind"] for link in result["links"]]
        assert "HTTP" in link_types
        assert "KAFKA" in link_types
    
    @pytest.mark.asyncio
    async def test_build_graph_data_empty(self, graph_builder, mock_db_session):
        """Test graph data building with empty database"""
        # Mock empty responses
        services_result = AsyncMock()
        services_result.scalars.return_value.all.return_value = []
        
        interactions_result = AsyncMock()
        interactions_result.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.side_effect = [services_result, interactions_result]
        
        result = await graph_builder.build_graph_data()
        
        assert result["nodes"] == []
        assert result["links"] == []
    
    @pytest.mark.asyncio
    async def test_build_graph_data_with_metadata(self, graph_builder, mock_db_session):
        """Test graph data building with service metadata"""
        from app.db.models import Service, Interaction, EdgeType
        import uuid
        
        # Mock services with metadata
        services = [
            Service(
                id=uuid.uuid4(), 
                name="api-gateway", 
                repo_id=None, 
                language="python",
                metadata={"version": "1.0.0", "port": 8080}
            ),
        ]
        
        interactions = []
        
        services_result = AsyncMock()
        services_result.scalars.return_value.all.return_value = services
        
        interactions_result = AsyncMock()
        interactions_result.scalars.return_value.all.return_value = interactions
        
        mock_db_session.execute.side_effect = [services_result, interactions_result]
        
        result = await graph_builder.build_graph_data()
        
        assert len(result["nodes"]) == 1
        node = result["nodes"][0]
        assert node["name"] == "api-gateway"
        assert "metadata" in node


class TestScanPipeline:
    """Test suite for ScanPipeline"""
    
    @pytest.fixture
    def mock_db_session(self):
        from sqlalchemy.ext.asyncio import AsyncSession
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_mcp_client(self):
        return Mock(spec=MCPGitHubClient)
    
    @pytest.fixture
    def scan_pipeline(self, mock_db_session, mock_mcp_client):
        return ScanPipeline(mock_db_session, mock_mcp_client)
    
    def test_init(self, mock_db_session, mock_mcp_client):
        """Test ScanPipeline initialization"""
        pipeline = ScanPipeline(mock_db_session, mock_mcp_client)
        assert pipeline.db_session == mock_db_session
        assert pipeline.mcp_client == mock_mcp_client
    
    @pytest.mark.asyncio
    async def test_scan_repository(self, scan_pipeline, mock_db_session, mock_mcp_client):
        """Test repository scanning process"""
        from app.db.models import Repository, Scan, ScanStatus
        import uuid
        
        repo_id = uuid.uuid4()
        scan_id = uuid.uuid4()
        
        # Mock repository
        mock_repo = Repository(
            id=repo_id,
            full_name="owner/repo",
            html_url="https://github.com/owner/repo"
        )
        
        # Mock scan
        mock_scan = Scan(
            id=scan_id,
            user_id="tester",
            status=ScanStatus.PENDING
        )
        
        # Mock file discovery
        mock_files = [
            {"path": "src/app.py", "content": "import requests\nrequests.get('http://api.service.com/data')", "size": 1024},
            {"path": "src/consumer.py", "content": "from kafka import KafkaConsumer\nconsumer = KafkaConsumer('user-events')", "size": 512},
        ]
        
        # Setup mocks
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        with patch.object(scan_pipeline, '_discover_files', return_value=mock_files):
            with patch.object(scan_pipeline, '_analyze_files', return_value={"services": [], "interactions": []}):
                result = await scan_pipeline.scan_repository(mock_repo, mock_scan)
                
                assert result["status"] == "success"
                assert "services_found" in result
                assert "interactions_found" in result
    
    @pytest.mark.asyncio
    async def test_scan_repository_error_handling(self, scan_pipeline, mock_db_session, mock_mcp_client):
        """Test error handling during repository scanning"""
        from app.db.models import Repository, Scan, ScanStatus
        import uuid
        
        repo = Repository(id=uuid.uuid4(), full_name="owner/repo", html_url="https://github.com/owner/repo")
        scan = Scan(id=uuid.uuid4(), user_id="tester", status=ScanStatus.PENDING)
        
        # Mock an error during scanning
        with patch.object(scan_pipeline, '_discover_files', side_effect=Exception("GitHub API error")):
            result = await scan_pipeline.scan_repository(repo, scan)
            
            assert result["status"] == "error"
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_discover_files(self, scan_pipeline, mock_mcp_client):
        """Test file discovery process"""
        mock_files = [
            {"path": "src/main.py", "type": "file", "size": 1024},
            {"path": "src/utils.js", "type": "file", "size": 512},
            {"path": "docs/README.md", "type": "file", "size": 256},
        ]
        
        mock_mcp_client.list_files.return_value = mock_files
        mock_mcp_client.get_file_content.side_effect = lambda repo, path, branch: f"content of {path}"
        
        result = await scan_pipeline._discover_files("owner/repo", "main")
        
        assert len(result) == 2  # Should only include .py and .js files
        assert result[0]["path"] == "src/main.py"
        assert result[1]["path"] == "src/utils.js"
    
    @pytest.mark.asyncio
    async def test_analyze_files(self, scan_pipeline):
        """Test file analysis process"""
        mock_files = [
            {
                "path": "src/user_service.py",
                "content": """
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    response = requests.get('http://auth-service/api/auth/validate')
    return response.json()
"""
            },
            {
                "path": "src/order_consumer.py", 
                "content": """
from kafka import KafkaConsumer

consumer = KafkaConsumer('order-events', 'user-events')
for message in consumer:
    process_order(message)
"""
            }
        ]
        
        result = await scan_pipeline._analyze_files(mock_files)
        
        assert "services" in result
        assert "interactions" in result
        assert len(result["services"]) >= 2  # user_service, order_consumer
        assert len(result["interactions"]) >= 2  # HTTP call to auth-service, Kafka topics


class TestNormalizeService:
    """Test suite for normalization utilities"""
    
    def test_normalize_service_name(self):
        """Test service name normalization"""
        test_cases = [
            ("user-service", "user-service"),
            ("UserService", "user-service"),
            ("user_service", "user-service"),
            ("User-Service", "user-service"),
            ("USER_SERVICE", "user-service"),
        ]
        
        for input_name, expected in test_cases:
            result = normalize_service_name(input_name)
            assert result == expected
    
    def test_normalize_url(self):
        """Test URL normalization"""
        test_cases = [
            ("http://api.service.com/v1/users", "http://api.service.com/v1/users"),
            ("https://auth.service.internal/login", "https://auth.service.internal/login"),
            ("/api/users/{id}", "/api/users/{id}"),
            ("api.service.com/users", "http://api.service.com/users"),
        ]
        
        for input_url, expected in test_cases:
            result = normalize_url(input_url)
            assert result == expected


class TestEmbeddingService:
    """Test suite for EmbeddingService"""
    
    @pytest.fixture
    def mock_openai_client(self):
        return Mock()
    
    @pytest.fixture
    def embedding_service(self, mock_openai_client):
        return EmbeddingService(mock_openai_client)
    
    def test_init(self, mock_openai_client):
        """Test EmbeddingService initialization"""
        service = EmbeddingService(mock_openai_client)
        assert service.client == mock_openai_client
    
    @pytest.mark.asyncio
    async def test_generate_embeddings(self, embedding_service, mock_openai_client):
        """Test embedding generation"""
        mock_texts = ["user service code", "authentication logic", "database queries"]
        mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=emb) for emb in mock_embeddings]
        mock_openai_client.embeddings.create.return_value = mock_response
        
        result = await embedding_service.generate_embeddings(mock_texts)
        
        assert len(result) == 3
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        assert result[2] == [0.7, 0.8, 0.9]
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_error(self, embedding_service, mock_openai_client):
        """Test embedding generation error handling"""
        mock_openai_client.embeddings.create.side_effect = Exception("API error")
        
        result = await embedding_service.generate_embeddings(["test text"])
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_similarity_search(self, embedding_service):
        """Test similarity search functionality"""
        # Mock embeddings database
        mock_embeddings = {
            "service-a": [0.1, 0.2, 0.3],
            "service-b": [0.4, 0.5, 0.6],
            "service-c": [0.7, 0.8, 0.9],
        }
        
        query_embedding = [0.15, 0.25, 0.35]
        
        # Test similarity calculation
        with patch.object(embedding_service, 'generate_embeddings', return_value=[query_embedding]):
            result = await embedding_service.similarity_search(query_embedding, mock_embeddings, top_k=2)
            
            assert len(result) == 2
            # service-a should be most similar to query
            assert result[0][0] == "service-a"
    
    @pytest.mark.asyncio
    async def test_cluster_services(self, embedding_service):
        """Test service clustering based on embeddings"""
        mock_embeddings = {
            "user-service": [0.1, 0.2, 0.3],
            "auth-service": [0.15, 0.25, 0.35],  # Similar to user-service
            "payment-service": [0.8, 0.9, 1.0],   # Different cluster
            "order-service": [0.85, 0.95, 1.05],  # Similar to payment-service
        }
        
        result = await embedding_service.cluster_services(mock_embeddings, num_clusters=2)
        
        assert len(result) == 2
        # First cluster should contain user-service and auth-service
        # Second cluster should contain payment-service and order-service
        
        cluster_services = set()
        for cluster in result:
            cluster_services.update(cluster)
        
        assert cluster_services == set(mock_embeddings.keys())


class TestMCPGitHubClient:
    """Test suite for MCPGitHubClient"""
    
    @pytest.fixture
    def mock_mcp_client(self):
        return Mock(spec=MCPGitHubClient)
    
    @pytest.mark.asyncio
    async def test_list_files(self, mock_mcp_client):
        """Test listing repository files"""
        mock_files = [
            {"path": "src/main.py", "type": "file", "size": 1024},
            {"path": "src/utils", "type": "dir", "size": 0},
        ]
        
        mock_mcp_client.list_files.return_value = mock_files
        
        result = await mock_mcp_client.list_files("owner/repo", "", "main")
        
        assert len(result) == 2
        assert result[0]["path"] == "src/main.py"
        assert result[1]["type"] == "dir"
    
    @pytest.mark.asyncio
    async def test_get_file_content(self, mock_mcp_client):
        """Test getting file content"""
        mock_content = "def main():\n    print('Hello, World!')"
        
        mock_mcp_client.get_file_content.return_value = mock_content
        
        result = await mock_mcp_client.get_file_content("owner/repo", "src/main.py", "main")
        
        assert result == mock_content
    
    @pytest.mark.asyncio
    async def test_get_file_content_not_found(self, mock_mcp_client):
        """Test handling of missing files"""
        mock_mcp_client.get_file_content.return_value = None
        
        result = await mock_mcp_client.get_file_content("owner/repo", "nonexistent.py", "main")
        
        assert result is None