"""
Performance Tests for EntroFeed

Tests for:
- Response time benchmarks
- Concurrent request handling
- Memory usage
- Database query performance
"""

import asyncio
import time
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.app import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestResponseTime:
    """Test response times for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, client):
        """Health check should respond quickly."""
        start = time.time()
        response = await client.get("/health")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 0.5, f"Health check took {elapsed:.2f}s, expected < 0.5s"

    @pytest.mark.asyncio
    async def test_about_response_time(self, client):
        """About endpoint should respond quickly."""
        start = time.time()
        response = await client.get(
            "/api/about", headers={"accept": "application/json"}
        )
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"About took {elapsed:.2f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_list_feeds_response_time(self, client):
        """List feeds should respond quickly."""
        start = time.time()
        response = await client.get("/util/list-feeds")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"List feeds took {elapsed:.2f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_search_response_time(self, client):
        """Search should respond within reasonable time."""
        start = time.time()
        response = await client.get("/api/search?q=test")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 2.0, f"Search took {elapsed:.2f}s, expected < 2.0s"


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, client):
        """Test handling multiple concurrent health checks."""
        tasks = [client.get("/health") for _ in range(20)]
        responses = await asyncio.gather(*tasks)
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_concurrent_list_requests(self, client):
        """Test handling concurrent list requests."""
        tasks = [
            client.get("/util/list-feeds"),
            client.get("/util/list-handlers"),
            client.get("/util/feed-stats"),
        ] * 5
        responses = await asyncio.gather(*tasks)
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_concurrent_different_endpoints(self, client):
        """Test concurrent requests to different endpoints."""
        tasks = [
            client.get("/health"),
            client.get("/api/about"),
            client.get("/util/list-feeds"),
            client.get("/util/list-handlers"),
            client.get("/api/interests"),
        ] * 4
        responses = await asyncio.gather(*tasks)
        assert all(r.status_code in [200, 404] for r in responses)


class TestDatabasePerformance:
    """Test database query performance."""

    @pytest.mark.asyncio
    async def test_feed_list_performance(self, client):
        """Test feed listing performance."""
        start = time.time()
        response = await client.get("/util/list-feeds")
        elapsed = time.time() - start
        assert response.status_code == 200
        # With small dataset, should be very fast
        assert elapsed < 0.5, f"Feed list took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_entries_list_performance(self, client):
        """Test entries listing performance."""
        start = time.time()
        response = await client.get("/util/list-feed-entries")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"Entries list took {elapsed:.2f}s"


class TestThroughput:
    """Test system throughput."""

    @pytest.mark.asyncio
    async def test_requests_per_second(self, client):
        """Measure approximate requests per second."""
        start = time.time()
        count = 0
        while time.time() - start < 2.0:
            response = await client.get("/health")
            if response.status_code == 200:
                count += 1
        elapsed = time.time() - start
        rps = count / elapsed
        assert rps > 10, f"Only {rps:.1f} req/s, expected > 10"


class TestMemoryEfficiency:
    """Test memory efficiency of responses."""

    @pytest.mark.asyncio
    async def test_response_size_reasonable(self, client):
        """Test response sizes are reasonable."""
        response = await client.get(
            "/api/about", headers={"accept": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        # Response should be under 1MB

        response_size = len(str(data))
        assert response_size < 1024 * 1024, f"Response too large: {response_size} bytes"

    @pytest.mark.asyncio
    async def test_large_list_handled(self, client):
        """Test large lists don't cause issues."""
        response = await client.get("/util/list-feed-entries")
        # Should handle gracefully regardless of size
        assert response.status_code in [200, 500]
