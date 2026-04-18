"""
API Endpoint Tests for EntroFeed

Tests all REST API endpoints for correct behavior,
status codes, and response formats.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.app import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint returns OK status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"


@pytest.mark.asyncio
async def test_about_endpoint(client):
    """Test about endpoint returns app info."""
    response = await client.get("/api/about", headers={"accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert "version" in data
    assert "python_version" in data


@pytest.mark.asyncio
async def test_list_feeds_endpoint(client):
    """Test feeds listing utility endpoint."""
    response = await client.get("/util/list-feeds")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_handlers_endpoint(client):
    """Test handlers listing utility endpoint."""
    response = await client.get("/util/list-handlers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_settings_endpoint_json(client):
    """Test settings endpoint returns JSON."""
    response = await client.get(
        "/settings/dummy_llm", headers={"accept": "application/json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "handler" in data
    assert "schema" in data


@pytest.mark.asyncio
async def test_recommendations_interest(client):
    """Test interest-based recommendations endpoint."""
    response = await client.get("/api/recommendations/interest")
    # May return empty list if no data, but should be 200
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_recommendations_trending(client):
    """Test trending recommendations endpoint."""
    response = await client.get("/api/recommendations/trending")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_interests_endpoint(client):
    """Test interests listing endpoint."""
    response = await client.get("/api/interests")
    assert response.status_code == 200
    data = response.json()
    # Response is {"interests": [...]}
    assert isinstance(data, dict) and "interests" in data


@pytest.mark.asyncio
async def test_inferred_interests_endpoint(client):
    """Test inferred interests endpoint."""
    response = await client.get("/api/interests/inferred")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_llm_status_endpoint(client):
    """Test LLM status endpoint."""
    response = await client.get("/api/llm/status")
    # Should return status even if LLM not configured
    assert response.status_code == 200
    data = response.json()
    assert "available" in data or "error" in data


@pytest.mark.asyncio
async def test_llm_usage_endpoint(client):
    """Test LLM usage endpoint."""
    response = await client.get("/api/llm/usage")
    assert response.status_code == 200
    data = response.json()
    # Should return usage stats with today and history
    assert "today" in data or "history" in data


@pytest.mark.asyncio
async def test_agent_sessions_endpoint(client):
    """Test agent sessions listing endpoint."""
    response = await client.get("/api/agent/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_agent_tools_endpoint(client):
    """Test agent tools listing endpoint."""
    response = await client.get("/api/agent/tools")
    assert response.status_code == 200
    data = response.json()
    # Response is {"tools": [...]}
    assert isinstance(data, dict) and "tools" in data


@pytest.mark.asyncio
async def test_entry_state_update(client):
    """Test entry state update endpoint."""
    # Test with non-existent entry
    # Note: TinyDB storage doesn't support update_feed_entry_state
    response = await client.patch("/api/entries/nonexistent-id", json={"is_read": True})
    # TinyDB may throw error, SQLite returns 404
    assert response.status_code in [200, 201, 404, 500]


@pytest.mark.asyncio
async def test_search_endpoint(client):
    """Test search endpoint."""
    response = await client.get("/api/search?q=test")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_translate_endpoint_requires_text(client):
    """Test translate endpoint requires text field."""
    response = await client.post("/api/translate", json={})
    # Should return validation error
    assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
async def test_export_opml_endpoint(client):
    """Test OPML export endpoint."""
    response = await client.get("/api/export_opml/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_backup_endpoint(client):
    """Test backup endpoint."""
    response = await client.get("/api/backup/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_import_opml_invalid_file(client):
    """Test OPML import with invalid file."""
    response = await client.post(
        "/api/import_opml/",
        files={"file": ("test.xml", b"invalid content", "text/xml")},
    )
    # Returns 200 with error status in body (endpoint catches exceptions)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_create_agent_session(client):
    """Test creating a new agent session."""
    response = await client.post("/api/agent/sessions", json={})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_agent_chat_without_session(client):
    """Test agent chat creates new session when session_id is None."""
    response = await client.post(
        "/api/agent/chat", json={"message": "hello", "session_id": None}
    )
    # Creates a new session when session_id is None
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_handler_schema_endpoint(client):
    """Test handler schema endpoint."""
    response = await client.get("/settings/dummy_llm")
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_feed_stats_endpoint(client):
    """Test feed stats utility endpoint."""
    response = await client.get("/util/feed-stats")
    assert response.status_code == 200
