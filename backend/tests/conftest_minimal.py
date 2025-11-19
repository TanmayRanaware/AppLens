"""Minimal conftest for running basic tests without full application dependencies"""
import os
import sys
import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

# Add parent directory to path for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set minimal environment variables
os.environ.setdefault("GITHUB_CLIENT_ID", "test-client")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_uuid():
    """Mock UUID for consistent testing"""
    import uuid
    from unittest.mock import patch
    
    test_uuid = uuid.UUID('12345678-1234-5678-1234-567812345678')
    
    with patch('uuid.uuid4', return_value=test_uuid):
        yield test_uuid


@pytest.fixture
def sample_service_data():
    """Sample service data for testing"""
    return {
        "id": "12345678-1234-5678-1234-567812345678",
        "name": "test-service",
        "language": "python",
        "repo_id": "87654321-4321-8765-4321-876543210987"
    }


@pytest.fixture
def sample_interaction_data():
    """Sample interaction data for testing"""
    return {
        "source_service_id": "12345678-1234-5678-1234-567812345678",
        "target_service_id": "87654321-4321-8765-4321-876543210987",
        "edge_type": "HTTP",
        "http_method": "GET",
        "http_url": "/api/test",
        "confidence": 0.9
    }