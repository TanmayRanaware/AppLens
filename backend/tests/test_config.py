no"""Unit tests for configuration and environment"""
import pytest
from unittest.mock import patch, Mock
import os

from app.config import Settings
from app.main import app
from app.auth.github_oauth import get_github_access_token, get_github_user


class TestSettings:
    """Test suite for application settings"""
    
    def test_default_settings(self):
        """Test default settings values"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            
            assert settings.postgres_url == "postgresql+asyncpg://applens:applens@localhost:5432/applens"
            assert settings.jwt_secret == "change-me-in-production"
            assert settings.jwt_algorithm == "HS256"
            assert settings.jwt_expiration_hours == 24
            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.frontend_url == "http://localhost:3000"
    
    def test_github_oauth_redirect_uri_computed(self):
        """Test GitHub OAuth redirect URI computation"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "FRONTEND_URL": "http://localhost:3000"
        }):
            settings = Settings()
            
            # Development environment
            computed_uri = settings.github_oauth_redirect_uri_computed
            assert computed_uri == "http://localhost:8000/auth/github/callback"
    
    def test_github_oauth_redirect_uri_production(self):
        """Test GitHub OAuth redirect URI in production"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "FRONTEND_URL": "https://app.example.com",
            "ENVIRONMENT": "production"
        }):
            settings = Settings()
            
            computed_uri = settings.github_oauth_redirect_uri_computed
            assert computed_uri == "https://app.example.com/api/auth/github/callback"
    
    def test_github_oauth_redirect_uri_explicit(self):
        """Test GitHub OAuth redirect URI with explicit setting"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "FRONTEND_URL": "http://localhost:3000",
            "GITHUB_OAUTH_REDIRECT_URI": "https://custom-callback.com/callback"
        }):
            settings = Settings()
            
            computed_uri = settings.github_oauth_redirect_uri_computed
            assert computed_uri == "https://custom-callback.com/callback"
    
    def test_required_environment_variables(self):
        """Test that required environment variables are handled correctly"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_openai_key"
        }, clear=True):
            settings = Settings()
            
            # Should not raise an exception
            assert settings.github_client_id == "test_client_id"
            assert settings.github_client_secret == "test_secret"
            assert settings.openai_api_key == "test_openai_key"
    
    def test_settings_validation(self):
        """Test settings validation"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_openai_key",
            "JWT_SECRET": "custom_secret",
            "DEBUG": "true",
            "ENVIRONMENT": "staging"
        }):
            settings = Settings()
            
            assert settings.jwt_secret == "custom_secret"
            assert settings.debug is True
            assert settings.environment == "staging"
    
    def test_settings_env_file_loading(self):
        """Test loading settings from .env file"""
        with patch('app.config.Path.exists') as mock_exists, \
             patch('app.config.settings_load_file') as mock_load:
            
            mock_exists.return_value = True
            mock_load.return_value = {
                "GITHUB_CLIENT_ID": "env_file_client_id",
                "GITHUB_CLIENT_SECRET": "env_file_secret",
                "OPENAI_API_KEY": "env_file_openai_key"
            }
            
            settings = Settings()
            
            assert settings.github_client_id == "env_file_client_id"
            assert settings.github_client_secret == "env_file_secret"
            assert settings.openai_api_key == "env_file_openai_key"


class TestAppConfiguration:
    """Test suite for FastAPI application configuration"""
    
    def test_app_initialization(self):
        """Test FastAPI app initialization"""
        assert app.title == "AppLens API"
        assert app.description == "Microservice Dependency Visualization API"
        assert app.version == "0.1.0"
        assert app.redirect_slashes is False
    
    def test_app_cors_middleware(self):
        """Test CORS middleware configuration"""
        # The CORS middleware is configured in the app
        # We can't directly test middleware in unit tests,
        # but we can verify the app has the middleware
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        
        # Verify CORS middleware is present
        from fastapi.middleware.cors import CORSMiddleware
        assert any(issubclass(middleware_type, CORSMiddleware) for middleware_type in middleware_types)
    
    def test_app_routers(self):
        """Test that all routers are included"""
        # Get all route paths
        routes = [route.path for route in app.routes]
        
        # Verify expected routes are present
        expected_routes = [
            "/auth",
            "/repos", 
            "/scan",
            "/graph",
            "/chat",
            "/nlq",
            "/health",
            "/"
        ]
        
        for expected_route in expected_routes:
            assert any(expected_route in route for route in routes), f"Route {expected_route} not found"
    
    def test_app_startup_event(self):
        """Test app startup event handler"""
        # The startup event is registered in the app
        # We can verify it exists by checking the event handlers
        startup_handlers = app.router.on_startup
        
        assert len(startup_handlers) > 0
        
        # Verify that startup function is registered
        startup_function_names = [handler.__name__ for handler in startup_handlers]
        assert "startup" in startup_function_names
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        from httpx import AsyncClient
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "applens-backend"
            assert data["version"] == "0.1.0"
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint"""
        from httpx import AsyncClient
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "docs" in data


class TestGitHubOAuth:
    """Test suite for GitHub OAuth functionality"""
    
    @pytest.fixture
    def mock_httpx_client(self):
        with patch('app.auth.github_oauth.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_get_github_access_token_success(self, mock_httpx_client):
        """Test successful GitHub access token exchange"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "gho_test123",
            "token_type": "bearer",
            "scope": "read:user,repo"
        }
        mock_httpx_client.post.return_value = mock_response
        
        result = await get_github_access_token("test_auth_code")
        
        assert result == "gho_test123"
        
        # Verify the request was made correctly
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        
        assert "https://github.com/login/oauth/access_token" in call_args[0][0]
        assert call_args[1]["data"]["client_id"] is not None
        assert call_args[1]["data"]["client_secret"] is not None
        assert call_args[1]["data"]["code"] == "test_auth_code"
    
    @pytest.mark.asyncio
    async def test_get_github_access_token_failure(self, mock_httpx_client):
        """Test GitHub access token exchange failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "The authorization code is invalid"
        }
        mock_httpx_client.post.return_value = mock_response
        
        result = await get_github_access_token("invalid_code")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_github_access_token_network_error(self, mock_httpx_client):
        """Test GitHub access token network error"""
        mock_httpx_client.post.side_effect = Exception("Network error")
        
        result = await get_github_access_token("test_code")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_github_user_success(self, mock_httpx_client):
        """Test successful GitHub user info retrieval"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://github.com/images/error/testuser_happy.gif"
        }
        mock_httpx_client.get.return_value = mock_response
        
        result = await get_github_user("test_access_token")
        
        assert result["id"] == 12345
        assert result["login"] == "testuser"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        
        # Verify the request was made correctly
        mock_httpx_client.get.assert_called_once()
        call_args = mock_httpx_client.get.call_args
        
        assert "https://api.github.com/user" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "token test_access_token"
    
    @pytest.mark.asyncio
    async def test_get_github_user_private_email(self, mock_httpx_client):
        """Test GitHub user info with private email"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": None,  # Private email
            "avatar_url": "https://github.com/images/error/testuser_happy.gif"
        }
        mock_httpx_client.get.return_value = mock_response
        
        result = await get_github_user("test_access_token")
        
        assert result["id"] == 12345
        assert result["login"] == "testuser"
        assert result["name"] == "Test User"
        assert result["email"] is None
    
    @pytest.mark.asyncio
    async def test_get_github_user_not_found(self, mock_httpx_client):
        """Test GitHub user not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest"
        }
        mock_httpx_client.get.return_value = mock_response
        
        result = await get_github_user("invalid_token")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_github_user_network_error(self, mock_httpx_client):
        """Test GitHub user info network error"""
        mock_httpx_client.get.side_effect = Exception("Network error")
        
        result = await get_github_user("test_token")
        
        assert result is None


class TestEnvironmentVariables:
    """Test suite for environment variable handling"""
    
    def test_required_vars_not_set(self):
        """Test behavior when required environment variables are not set"""
        with patch.dict(os.environ, {}, clear=True):
            # This should not raise an exception during Settings creation
            # but accessing the values should work with defaults
            settings = Settings()
            
            # Test that defaults are used
            assert settings.postgres_url is not None
            assert settings.jwt_secret is not None
    
    def test_malformed_environment(self):
        """Test handling of malformed environment variables"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_openai_key",
            "JWT_EXPIRATION_HOURS": "invalid_number"  # Should be integer
        }):
            # Pydantic should handle the conversion
            settings = Settings()
            
            # The malformed value should either use default or raise validation error
            try:
                # If it doesn't raise, it should use default
                assert isinstance(settings.jwt_expiration_hours, int)
            except ValueError:
                # Or it should raise a validation error
                pass
    
    def test_frontend_url_validation(self):
        """Test frontend URL validation"""
        test_cases = [
            ("http://localhost:3000", True),
            ("https://app.example.com", True),
            ("localhost:3000", False),  # Missing protocol
            ("", False),  # Empty
            ("not-a-url", False),  # Invalid URL
        ]
        
        for url, should_be_valid in test_cases:
            with patch.dict(os.environ, {
                "GITHUB_CLIENT_ID": "test_client_id",
                "GITHUB_CLIENT_SECRET": "test_secret", 
                "OPENAI_API_KEY": "test_openai_key",
                "FRONTEND_URL": url
            }):
                if should_be_valid:
                    # Should not raise an exception
                    settings = Settings()
                    assert settings.frontend_url == url
                else:
                    # Should raise validation error
                    with pytest.raises(Exception):
                        Settings()
    
    def test_database_url_validation(self):
        """Test database URL validation"""
        test_cases = [
            ("postgresql+asyncpg://user:pass@localhost:5432/db", True),
            ("postgresql://user:pass@localhost:5432/db", True),
            ("sqlite:///test.db", True),
            ("invalid://connection", False),
            ("", False),
        ]
        
        for url, should_be_valid in test_cases:
            with patch.dict(os.environ, {
                "GITHUB_CLIENT_ID": "test_client_id",
                "GITHUB_CLIENT_SECRET": "test_secret",
                "OPENAI_API_KEY": "test_openai_key",
                "POSTGRES_URL": url
            }):
                if should_be_valid:
                    settings = Settings()
                    assert settings.postgres_url == url
                else:
                    with pytest.raises(Exception):
                        Settings()


class TestSecurityConfiguration:
    """Test suite for security-related configuration"""
    
    def test_jwt_configuration(self):
        """Test JWT token configuration"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_openai_key",
            "JWT_SECRET": "super_secret_key_123",
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_HOURS": "48"
        }):
            settings = Settings()
            
            assert settings.jwt_secret == "super_secret_key_123"
            assert settings.jwt_algorithm == "HS256"
            assert settings.jwt_expiration_hours == 48
    
    def test_production_security_settings(self):
        """Test security settings for production environment"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_openai_key",
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "JWT_SECRET": "very_secure_production_secret"
        }):
            settings = Settings()
            
            assert settings.environment == "production"
            assert settings.debug is False
            assert settings.jwt_secret == "very_secure_production_secret"
    
    def test_development_security_settings(self):
        """Test security settings for development environment"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_openai_key",
            "ENVIRONMENT": "development",
            "DEBUG": "true"
        }):
            settings = Settings()
            
            assert settings.environment == "development"
            assert settings.debug is True
    
    def test_mcp_configuration(self):
        """Test MCP (Model Context Protocol) configuration"""
        with patch.dict(os.environ, {
            "GITHUB_CLIENT_ID": "test_client_id",
            "GITHUB_CLIENT_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_openai_key",
            "MCP_GITHUB_HOST": "mcp.example.com",
            "MCP_GITHUB_PORT": "8080"
        }):
            settings = Settings()
            
            assert settings.mcp_github_host == "mcp.example.com"
            assert settings.mcp_github_port == 8080