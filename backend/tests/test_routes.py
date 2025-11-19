"""Unit tests for API routes"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid

from app.main import app
from app.routes import auth, scan, nlq, repos
from app.auth.github_oauth import get_github_access_token, get_github_user


class TestAuthRoutes:
    """Test suite for authentication routes"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_github_oauth(self):
        with patch('app.auth.github_oauth.get_github_access_token') as mock_get_token, \
             patch('app.auth.github_oauth.get_github_user') as mock_get_user:
            
            # Mock successful token exchange
            mock_get_token.return_value = "mock_access_token"
            
            # Mock successful user info retrieval
            mock_get_user.return_value = {
                "id": 12345,
                "login": "testuser",
                "name": "Test User",
                "email": "test@example.com"
            }
            
            yield {
                "get_token": mock_get_token,
                "get_user": mock_get_user
            }
    
    def test_github_login_redirect(self, client):
        """Test GitHub OAuth login redirect"""
        response = client.get("/auth/github/login")
        
        assert response.status_code == 307  # Redirect
        assert response.headers["location"].startswith("https://github.com/login/oauth/authorize")
        assert "client_id=" in response.headers["location"]
        assert "scope=" in response.headers["location"]
    
    @pytest.mark.asyncio
    async def test_github_callback_success(self, client, mock_github_oauth):
        """Test successful GitHub OAuth callback"""
        response = client.get(
            "/auth/github/callback",
            params={"code": "mock_auth_code"}
        )
        
        assert response.status_code == 307  # Redirect to dashboard
        assert response.headers["location"] == "http://localhost:3000/dashboard"
        
        # Check that cookie is set
        assert "applens_token" in response.cookies
        token = response.cookies["applens_token"]
        assert len(token) > 0  # JWT token should be present
        
        # Verify OAuth functions were called
        mock_github_oauth["get_token"].assert_called_once_with("mock_auth_code")
        mock_github_oauth["get_user"].assert_called_once_with("mock_access_token")
    
    @pytest.mark.asyncio
    async def test_github_callback_missing_code(self, client):
        """Test GitHub OAuth callback with missing code"""
        response = client.get("/auth/github/callback")
        
        assert response.status_code == 400
        assert "Missing authorization code" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_github_callback_token_failure(self, client):
        """Test GitHub OAuth callback with token exchange failure"""
        with patch('app.auth.github_oauth.get_github_access_token', return_value=None):
            response = client.get(
                "/auth/github/callback",
                params={"code": "invalid_code"}
            )
            
            assert response.status_code == 400
            assert "Failed to get access token" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_github_callback_user_failure(self, client):
        """Test GitHub OAuth callback with user info failure"""
        with patch('app.auth.github_oauth.get_github_access_token', return_value="mock_token"), \
             patch('app.auth.github_oauth.get_github_user', return_value=None):
            
            response = client.get(
                "/auth/github/callback",
                params={"code": "mock_code"}
            )
            
            assert response.status_code == 400
            assert "Failed to get user info" in response.json()["detail"]
    
    def test_get_current_user_valid_token(self, client):
        """Test getting current user with valid token"""
        # Create a valid JWT token
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        payload = {
            "sub": "12345",
            "login": "testuser",
            "access_token": "mock_token",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        # Set cookie and make request
        client.cookies.set("applens_token", token)
        response = client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "12345"
        assert data["login"] == "testuser"
        assert data["authenticated"] is True
    
    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        client.cookies.set("applens_token", "invalid_token")
        response = client.get("/auth/me")
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    def test_logout(self, client):
        """Test user logout"""
        response = client.post("/auth/logout")
        
        assert response.status_code == 200
        # Cookie should be cleared
        assert client.cookies["applens_token"] == ""


class TestScanRoutes:
    """Test suite for scan routes"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        # Create valid auth headers
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        payload = {
            "sub": "12345",
            "login": "testuser",
            "access_token": "mock_token",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return {"Cookie": f"applens_token={token}"}
    
    @pytest.mark.asyncio
    async def test_initiate_scan_success(self, client, auth_headers):
        """Test successful scan initiation"""
        with patch('app.routes.scan.ScanPipeline') as mock_pipeline:
            mock_scan_instance = AsyncMock()
            mock_scan_instance.scan_repository.return_value = {
                "status": "success",
                "services_found": 3,
                "interactions_found": 5
            }
            mock_pipeline.return_value = mock_scan_instance
            
            response = client.post(
                "/scan/initiate",
                json={"repos": ["owner/repo1", "owner/repo2"]},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "scan_id" in data
            assert data["status"] == "initiated"
    
    @pytest.mark.asyncio
    async def test_initiate_scan_no_auth(self, client):
        """Test scan initiation without authentication"""
        response = client.post(
            "/scan/initiate",
            json={"repos": ["owner/repo"]}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_scan_status(self, client, auth_headers):
        """Test getting scan status"""
        scan_id = str(uuid.uuid4())
        
        # Mock scan status
        with patch('app.routes.scan.get_scan_status') as mock_get_status:
            mock_get_status.return_value = {
                "id": scan_id,
                "status": "running",
                "progress": 50,
                "services_found": 2,
                "interactions_found": 3
            }
            
            response = client.get(f"/scan/{scan_id}/status", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"
            assert data["progress"] == 50
    
    @pytest.mark.asyncio
    async def test_get_scan_status_not_found(self, client, auth_headers):
        """Test getting status of non-existent scan"""
        with patch('app.routes.scan.get_scan_status', return_value=None):
            scan_id = str(uuid.uuid4())
            response = client.get(f"/scan/{scan_id}/status", headers=auth_headers)
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_scans(self, client, auth_headers):
        """Test listing user scans"""
        with patch('app.routes.scan.list_user_scans') as mock_list_scans:
            mock_list_scans.return_value = [
                {
                    "id": str(uuid.uuid4()),
                    "status": "completed",
                    "created_at": "2025-01-01T00:00:00Z",
                    "repos": ["owner/repo1"]
                },
                {
                    "id": str(uuid.uuid4()),
                    "status": "failed",
                    "created_at": "2025-01-02T00:00:00Z",
                    "repos": ["owner/repo2"]
                }
            ]
            
            response = client.get("/scan/list", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["status"] == "completed"
            assert data[1]["status"] == "failed"


class TestNLQRoutes:
    """Test suite for natural language query routes"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        payload = {
            "sub": "12345",
            "login": "testuser",
            "access_token": "mock_token",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return {"Cookie": f"applens_token={token}"}
    
    @pytest.mark.asyncio
    async def test_natural_language_query(self, client, auth_headers):
        """Test natural language query processing"""
        with patch('app.routes.nlq.NLQAgent') as mock_agent_class:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.query.return_value = {
                "results": {"answer": "User service calls authentication service"},
                "graph_hints": {"highlight_services": ["user-service", "auth-service"]}
            }
            mock_agent_class.return_value = mock_agent_instance
            
            response = client.post(
                "/nlq",
                json={"question": "Which services call the auth service?"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "graph_hints" in data
            assert "answer" in data["results"]
    
    @pytest.mark.asyncio
    async def test_natural_language_query_no_auth(self, client):
        """Test NLQ without authentication"""
        response = client.post(
            "/nlq",
            json={"question": "What services exist?"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_natural_language_query_empty_question(self, client, auth_headers):
        """Test NLQ with empty question"""
        response = client.post(
            "/nlq",
            json={"question": ""},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Question cannot be empty" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_natural_language_query_error(self, client, auth_headers):
        """Test NLQ with processing error"""
        with patch('app.routes.nlq.NLQAgent') as mock_agent_class:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.query.side_effect = Exception("Processing error")
            mock_agent_class.return_value = mock_agent_instance
            
            response = client.post(
                "/nlq",
                json={"question": "Test question"},
                headers=auth_headers
            )
            
            assert response.status_code == 500
            assert "Failed to process question" in response.json()["detail"]


class TestReposRoutes:
    """Test suite for repository routes"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        payload = {
            "sub": "12345",
            "login": "testuser",
            "access_token": "mock_token",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return {"Cookie": f"applens_token={token}"}
    
    @pytest.mark.asyncio
    async def test_list_repositories(self, client, auth_headers):
        """Test listing user repositories"""
        with patch('app.routes.repos.get_user_repositories') as mock_get_repos:
            mock_get_repos.return_value = [
                {
                    "full_name": "owner/repo1",
                    "html_url": "https://github.com/owner/repo1",
                    "description": "First repository",
                    "language": "Python",
                    "private": False
                },
                {
                    "full_name": "owner/repo2",
                    "html_url": "https://github.com/owner/repo2",
                    "description": "Second repository",
                    "language": "JavaScript",
                    "private": True
                }
            ]
            
            response = client.get("/repos/list", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["full_name"] == "owner/repo1"
            assert data[0]["language"] == "Python"
            assert data[1]["private"] is True
    
    @pytest.mark.asyncio
    async def test_list_repositories_no_auth(self, client):
        """Test repository listing without authentication"""
        response = client.get("/repos/list")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_repository_details(self, client, auth_headers):
        """Test getting repository details"""
        repo_full_name = "owner/repo"
        
        with patch('app.routes.repos.get_repository_details') as mock_get_details:
            mock_get_details.return_value = {
                "full_name": repo_full_name,
                "html_url": "https://github.com/owner/repo",
                "description": "Test repository",
                "language": "Python",
                "stars": 42,
                "forks": 7,
                "default_branch": "main",
                "last_scanned": "2025-01-01T00:00:00Z"
            }
            
            response = client.get(f"/repos/{repo_full_name}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["full_name"] == repo_full_name
            assert data["stars"] == 42
            assert data["default_branch"] == "main"
    
    @pytest.mark.asyncio
    async def test_get_repository_details_not_found(self, client, auth_headers):
        """Test getting details of non-existent repository"""
        with patch('app.routes.repos.get_repository_details', return_value=None):
            response = client.get("/repos/nonexistent/repo", headers=auth_headers)
            
            assert response.status_code == 404
            assert "Repository not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_sync_repository(self, client, auth_headers):
        """Test repository synchronization"""
        repo_full_name = "owner/repo"
        
        with patch('app.routes.repos.sync_repository') as mock_sync:
            mock_sync.return_value = {
                "status": "success",
                "services_found": 5,
                "interactions_found": 12,
                "last_scan": "2025-01-01T00:00:00Z"
            }
            
            response = client.post(f"/repos/{repo_full_name}/sync", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["services_found"] == 5
            assert data["interactions_found"] == 12
    
    @pytest.mark.asyncio
    async def test_remove_repository(self, client, auth_headers):
        """Test repository removal"""
        repo_full_name = "owner/repo"
        
        with patch('app.routes.repos.remove_repository') as mock_remove:
            mock_remove.return_value = {"status": "removed"}
            
            response = client.delete(f"/repos/{repo_full_name}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "removed"
            mock_remove.assert_called_once_with(repo_full_name)


class TestChatRoutes:
    """Test suite for chat routes"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import settings
        
        payload = {
            "sub": "12345",
            "login": "testuser",
            "access_token": "mock_token",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return {"Cookie": f"applens_token={token}"}
    
    @pytest.mark.asyncio
    async def test_error_analyzer(self, client, auth_headers):
        """Test error analyzer endpoint"""
        with patch('app.routes.chat.ErrorAgent') as mock_agent_class:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.analyze.return_value = {
                "source_node": "user-service",
                "affected_nodes": ["auth-service", "order-service"],
                "reasoning": "Error in user-service affected downstream services",
                "confidence": 0.8
            }
            mock_agent_class.return_value = mock_agent_instance
            
            response = client.post(
                "/chat/error-analyzer",
                json={"log_text": "ERROR in user-service: connection timeout"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "source_node" in data
            assert "affected_nodes" in data
            assert "reasoning" in data
    
    @pytest.mark.asyncio
    async def test_what_if_simulator(self, client, auth_headers):
        """Test what-if simulator endpoint"""
        with patch('app.routes.chat.WhatIfAgent') as mock_agent_class:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.simulate.return_value = {
                "changed_service_ids": ["payment-service"],
                "blast_radius_nodes": ["order-service", "user-service"],
                "reasoning": "Changing payment API will affect dependent services",
                "risk_level": "medium"
            }
            mock_agent_class.return_value = mock_agent_instance
            
            response = client.post(
                "/chat/what-if",
                json={
                    "change_description": "Update payment API endpoint",
                    "repo": "owner/payment-service"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "changed_service_ids" in data
            assert "blast_radius_nodes" in data
            assert "risk_level" in data
    
    @pytest.mark.asyncio
    async def test_nlq_chat(self, client, auth_headers):
        """Test NLQ chat endpoint"""
        with patch('app.routes.chat.NLQAgent') as mock_agent_class:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.query.return_value = {
                "results": {"answer": "User service has 3 dependencies"},
                "graph_hints": {"highlight_services": ["user-service", "auth-service", "order-service"]}
            }
            mock_agent_class.return_value = mock_agent_instance
            
            response = client.post(
                "/chat/nlq",
                json={"question": "What does user-service depend on?"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "graph_hints" in data