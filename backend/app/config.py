"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    postgres_url: str = "postgresql+asyncpg://applens:applens@localhost:5432/applens"
    
    # GitHub OAuth
    github_client_id: str
    github_client_secret: str
    github_oauth_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    
    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # OpenAI
    openai_api_key: str
    
    # MCP GitHub Server
    mcp_github_host: str = "localhost"
    mcp_github_port: int = 8000
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Frontend URL
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()

