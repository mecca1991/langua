import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_request_id_header_present(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36


@pytest.mark.anyio
async def test_request_id_is_unique(client):
    response1 = await client.get("/health")
    response2 = await client.get("/health")
    assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]
