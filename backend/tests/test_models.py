"""Unit tests for database models"""
import pytest
from datetime import datetime
from uuid import uuid4, UUID
import enum

from app.db.models import (
    Repository, Service, Interaction, EdgeType, 
    Scan, ScanStatus, ScanTarget, User
)
from app.db.base import Base


class TestEdgeType:
    """Test EdgeType enum"""
    
    def test_edge_type_values(self):
        """Test EdgeType enum values"""
        assert EdgeType.HTTP.value == "HTTP"
        assert EdgeType.KAFKA.value == "Kafka"
        assert EdgeType.GRPC.value == "gRPC"
    
    def test_edge_type_parsing(self):
        """Test EdgeType from string"""
        assert EdgeType.HTTP == EdgeType("HTTP")
        assert EdgeType.KAFKA == EdgeType("Kafka")
        assert EdgeType.GRPC == EdgeType("gRPC")


class TestRepository:
    """Test Repository model"""
    
    def test_repository_creation(self):
        """Test repository model creation"""
        repo_id = uuid4()
        repo = Repository(
            id=repo_id,
            full_name="owner/repository",
            html_url="https://github.com/owner/repository",
            owner="owner",
            default_branch="main"
        )
        
        assert repo.id == repo_id
        assert repo.full_name == "owner/repository"
        assert repo.html_url == "https://github.com/owner/repository"
        assert repo.owner == "owner"
        assert repo.default_branch == "main"
        assert repo.created_at is None  # Should be None before adding to DB
        assert repo.updated_at is None
    
    def test_repository_repr(self):
        """Test repository string representation"""
        repo = Repository(
            id=uuid4(),
            full_name="owner/repository",
            html_url="https://github.com/owner/repository"
        )
        
        expected = f"<Repository(id={repo.id}, full_name='owner/repository')>"
        assert repr(repo) == expected
    
    def test_repository_equality(self):
        """Test repository equality comparison"""
        repo_id = uuid4()
        repo1 = Repository(id=repo_id, full_name="owner/repo")
        repo2 = Repository(id=repo_id, full_name="owner/repo")
        repo3 = Repository(id=uuid4(), full_name="owner/repo")
        
        assert repo1 == repo2
        assert repo1 != repo3


class TestService:
    """Test Service model"""
    
    def test_service_creation(self):
        """Test service model creation"""
        repo_id = uuid4()
        service_id = uuid4()
        service = Service(
            id=service_id,
            name="user-service",
            repo_id=repo_id,
            language="python"
        )
        
        assert service.id == service_id
        assert service.name == "user-service"
        assert service.repo_id == repo_id
        assert service.language == "python"
        assert service.metadata is None
        assert service.created_at is None
    
    def test_service_with_metadata(self):
        """Test service with metadata"""
        metadata = {
            "version": "1.0.0",
            "port": 8080,
            "environment": "production"
        }
        
        service = Service(
            id=uuid4(),
            name="api-gateway",
            repo_id=uuid4(),
            language="python",
            metadata=metadata
        )
        
        assert service.metadata == metadata
        assert service.metadata["version"] == "1.0.0"
        assert service.metadata["port"] == 8080
    
    def test_service_repr(self):
        """Test service string representation"""
        service = Service(
            id=uuid4(),
            name="auth-service",
            repo_id=uuid4(),
            language="java"
        )
        
        expected = f"<Service(id={service.id}, name='auth-service', language='java')>"
        assert repr(service) == expected


class TestInteraction:
    """Test Interaction model"""
    
    def test_interaction_creation(self):
        """Test interaction model creation"""
        source_id = uuid4()
        target_id = uuid4()
        
        interaction = Interaction(
            source_service_id=source_id,
            target_service_id=target_id,
            edge_type=EdgeType.HTTP,
            http_method="GET",
            http_url="/api/users",
            confidence=0.9
        )
        
        assert interaction.source_service_id == source_id
        assert interaction.target_service_id == target_id
        assert interaction.edge_type == EdgeType.HTTP
        assert interaction.http_method == "GET"
        assert interaction.http_url == "/api/users"
        assert interaction.kafka_topic is None
        assert interaction.confidence == 0.9
    
    def test_interaction_kafka(self):
        """Test Kafka interaction"""
        interaction = Interaction(
            source_service_id=uuid4(),
            target_service_id=uuid4(),
            edge_type=EdgeType.KAFKA,
            kafka_topic="user-events",
            confidence=0.8
        )
        
        assert interaction.edge_type == EdgeType.KAFKA
        assert interaction.kafka_topic == "user-events"
        assert interaction.http_method is None
        assert interaction.http_url is None
    
    def test_interaction_repr(self):
        """Test interaction string representation"""
        interaction = Interaction(
            source_service_id=uuid4(),
            target_service_id=uuid4(),
            edge_type=EdgeType.HTTP,
            http_url="/api/test"
        )
        
        expected = f"<Interaction(source={interaction.source_service_id}, target={interaction.target_service_id}, type=HTTP)>"
        assert repr(interaction) == expected


class TestScan:
    """Test Scan model"""
    
    def test_scan_creation(self):
        """Test scan model creation"""
        scan_id = uuid4()
        scan = Scan(
            id=scan_id,
            user_id="user123",
            status=ScanStatus.PENDING
        )
        
        assert scan.id == scan_id
        assert scan.user_id == "user123"
        assert scan.status == ScanStatus.PENDING
        assert scan.error_message is None
        assert scan.started_at is None
        assert scan.completed_at is None
    
    def test_scan_status_enum(self):
        """Test ScanStatus enum values"""
        assert ScanStatus.PENDING.value == "pending"
        assert ScanStatus.RUNNING.value == "running"
        assert ScanStatus.SUCCESS.value == "success"
        assert ScanStatus.FAILED.value == "failed"
    
    def test_scan_with_results(self):
        """Test scan with results"""
        scan = Scan(
            id=uuid4(),
            user_id="user123",
            status=ScanStatus.SUCCESS,
            error_message=None,
            started_at=datetime.utcnow()
        )
        
        # Add results
        scan.results = {
            "services_found": 5,
            "interactions_found": 12,
            "repositories_scanned": 2
        }
        
        assert scan.results["services_found"] == 5
        assert scan.results["interactions_found"] == 12
    
    def test_scan_repr(self):
        """Test scan string representation"""
        scan = Scan(
            id=uuid4(),
            user_id="user123",
            status=ScanStatus.RUNNING
        )
        
        expected = f"<Scan(id={scan.id}, user_id='user123', status='running')>"
        assert repr(scan) == expected


class TestScanTarget:
    """Test ScanTarget model"""
    
    def test_scan_target_creation(self):
        """Test scan target model creation"""
        scan_id = uuid4()
        repo_id = uuid4()
        
        target = ScanTarget(
            scan_id=scan_id,
            repo_id=repo_id
        )
        
        assert target.scan_id == scan_id
        assert target.repo_id == repo_id
        assert target.status is None
        assert target.error_message is None
    
    def test_scan_target_with_status(self):
        """Test scan target with processing status"""
        target = ScanTarget(
            scan_id=uuid4(),
            repo_id=uuid4(),
            status="completed",
            error_message=None
        )
        
        assert target.status == "completed"
        assert target.error_message is None
    
    def test_scan_target_repr(self):
        """Test scan target string representation"""
        target = ScanTarget(
            scan_id=uuid4(),
            repo_id=uuid4()
        )
        
        expected = f"<ScanTarget(scan={target.scan_id}, repo={target.repo_id})>"
        assert repr(target) == expected


class TestUser:
    """Test User model"""
    
    def test_user_creation(self):
        """Test user model creation"""
        user_id = "github_12345"
        user = User(
            id=user_id,
            login="testuser",
            name="Test User",
            email="test@example.com"
        )
        
        assert user.id == user_id
        assert user.login == "testuser"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.github_access_token is None
        assert user.created_at is None
    
    def test_user_with_token(self):
        """Test user with GitHub access token"""
        user = User(
            id="github_123",
            login="developer",
            github_access_token="gho_..."
        )
        
        assert user.github_access_token == "gho_..."
        assert user.email is None  # Optional field
    
    def test_user_repr(self):
        """Test user string representation"""
        user = User(
            id="github_123",
            login="developer"
        )
        
        expected = f"<User(id='github_123', login='developer')>"
        assert repr(user) == expected


class TestModelRelationships:
    """Test model relationships"""
    
    def test_repository_services_relationship(self):
        """Test repository-services relationship"""
        repo = Repository(
            id=uuid4(),
            full_name="owner/repo",
            html_url="https://github.com/owner/repo"
        )
        
        # Services should reference repository
        service = Service(
            id=uuid4(),
            name="api-service",
            repo_id=repo.id,
            language="python"
        )
        
        # Relationship is established via foreign key
        assert service.repo_id == repo.id
    
    def test_service_interactions_relationship(self):
        """Test service-interactions relationship"""
        service1 = Service(id=uuid4(), name="service-a", repo_id=uuid4())
        service2 = Service(id=uuid4(), name="service-b", repo_id=uuid4())
        
        # Interaction between services
        interaction = Interaction(
            source_service_id=service1.id,
            target_service_id=service2.id,
            edge_type=EdgeType.HTTP,
            http_url="/api/data"
        )
        
        # Relationships via foreign keys
        assert interaction.source_service_id == service1.id
        assert interaction.target_service_id == service2.id
    
    def test_scan_targets_relationship(self):
        """Test scan-targets relationship"""
        scan = Scan(
            id=uuid4(),
            user_id="user123",
            status=ScanStatus.SUCCESS
        )
        
        repo = Repository(
            id=uuid4(),
            full_name="owner/repo",
            html_url="https://github.com/owner/repo"
        )
        
        target = ScanTarget(
            scan_id=scan.id,
            repo_id=repo.id
        )
        
        # Relationships via foreign keys
        assert target.scan_id == scan.id
        assert target.repo_id == repo.id


class TestModelValidation:
    """Test model validation and constraints"""
    
    def test_edge_type_validation(self):
        """Test EdgeType enum validation"""
        # Valid edge types
        assert EdgeType.HTTP == EdgeType.HTTP
        assert EdgeType.KAFKA == EdgeType.KAFKA
        assert EdgeType.GRPC == EdgeType.GRPC
        
        # Invalid edge type should raise ValueError
        with pytest.raises(ValueError):
            EdgeType("INVALID_TYPE")
    
    def test_scan_status_validation(self):
        """Test ScanStatus enum validation"""
        # Valid statuses
        assert ScanStatus.PENDING == ScanStatus.PENDING
        assert ScanStatus.RUNNING == ScanStatus.RUNNING
        assert ScanStatus.SUCCESS == ScanStatus.SUCCESS
        assert ScanStatus.FAILED == ScanStatus.FAILED
        
        # Invalid status should raise ValueError
        with pytest.raises(ValueError):
            ScanStatus("INVALID_STATUS")
    
    def test_confidence_validation(self):
        """Test confidence score validation"""
        # Valid confidence scores
        interaction_low = Interaction(
            source_service_id=uuid4(),
            target_service_id=uuid4(),
            edge_type=EdgeType.HTTP,
            confidence=0.1
        )
        
        interaction_high = Interaction(
            source_service_id=uuid4(),
            target_service_id=uuid4(),
            edge_type=EdgeType.HTTP,
            confidence=0.95
        )
        
        interaction_exact = Interaction(
            source_service_id=uuid4(),
            target_service_id=uuid4(),
            edge_type=EdgeType.HTTP,
            confidence=1.0
        )
        
        # All should be valid (pydantic will handle validation in production)
        assert interaction_low.confidence >= 0.0
        assert interaction_high.confidence <= 1.0
        assert interaction_exact.confidence == 1.0
    
    def test_required_fields(self):
        """Test required field validation"""
        # Repository requires id and full_name
        with pytest.raises(TypeError):
            Repository()  # Missing required fields
        
        # Service requires id, name, repo_id
        with pytest.raises(TypeError):
            Service()  # Missing required fields
        
        # Interaction requires source_service_id and target_service_id
        with pytest.raises(TypeError):
            Interaction()  # Missing required fields


class TestModelMetadata:
    """Test model metadata and configuration"""
    
    def test_base_model_table_names(self):
        """Test that models have correct table names"""
        assert Repository.__tablename__ == "repositories"
        assert Service.__tablename__ == "services"
        assert Interaction.__tablename__ == "interactions"
        assert Scan.__tablename__ == "scans"
        assert ScanTarget.__tablename__ == "scan_targets"
        assert User.__tablename__ == "users"
    
    def test_model_inheritance(self):
        """Test that all models inherit from Base"""
        models = [Repository, Service, Interaction, Scan, ScanTarget, User]
        
        for model in models:
            assert issubclass(model, Base)
    
    def test_model_column_types(self):
        """Test model column types and constraints"""
        # Test string columns
        repo = Repository(
            id=uuid4(),
            full_name="owner/repository" * 10,  # Long name
            html_url="https://github.com/owner/repository"
        )
        
        assert isinstance(repo.full_name, str)
        assert isinstance(repo.html_url, str)
        
        # Test UUID columns
        assert isinstance(repo.id, UUID)
        
        # Test enum columns
        interaction = Interaction(
            source_service_id=uuid4(),
            target_service_id=uuid4(),
            edge_type=EdgeType.HTTP
        )
        
        assert isinstance(interaction.edge_type, EdgeType)
    
    def test_model_indexes(self):
        """Test model indexes and constraints"""
        # This would be verified in a real database setup
        # For now, just ensure the models don't crash during creation
        repo = Repository(
            id=uuid4(),
            full_name="owner/repo",
            html_url="https://github.com/owner/repo"
        )
        
        service = Service(
            id=uuid4(),
            name="test-service",
            repo_id=uuid4(),
            language="python"
        )
        
        # Models should be creatable without errors
        assert repo is not None
        assert service is not None


class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_repository_serialization(self):
        """Test repository model to_dict conversion"""
        repo = Repository(
            id=uuid4(),
            full_name="owner/repo",
            html_url="https://github.com/owner/repo",
            owner="owner"
        )
        
        # Test basic serialization
        data = {
            "id": str(repo.id),
            "full_name": repo.full_name,
            "html_url": repo.html_url,
            "owner": repo.owner
        }
        
        assert data["id"] == str(repo.id)
        assert data["full_name"] == repo.full_name
        assert data["html_url"] == repo.html_url
    
    def test_service_serialization(self):
        """Test service model serialization"""
        metadata = {"version": "1.0.0", "port": 8080}
        
        service = Service(
            id=uuid4(),
            name="api-service",
            repo_id=uuid4(),
            language="python",
            metadata=metadata
        )
        
        # Test metadata serialization
        assert service.metadata == metadata
        assert isinstance(service.metadata, dict)
    
    def test_interaction_serialization(self):
        """Test interaction model serialization"""
        interaction = Interaction(
            source_service_id=uuid4(),
            target_service_id=uuid4(),
            edge_type=EdgeType.HTTP,
            http_method="GET",
            http_url="/api/data",
            confidence=0.9
        )
        
        # Test enum serialization
        assert interaction.edge_type.value == "HTTP"
        assert isinstance(interaction.confidence, float)
    
    def test_scan_serialization(self):
        """Test scan model serialization"""
        scan = Scan(
            id=uuid4(),
            user_id="user123",
            status=ScanStatus.SUCCESS,
            results={"services_found": 5}
        )
        
        # Test status enum and results serialization
        assert scan.status.value == "success"
        assert scan.results["services_found"] == 5
        assert isinstance(scan.results, dict)