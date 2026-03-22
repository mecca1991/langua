import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from jose.utils import base64url_encode
from httpx import ASGITransport, AsyncClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.main import app

TEST_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


@pytest.fixture
def valid_token():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "user_metadata": {"full_name": "Test User", "avatar_url": "https://example.com/avatar.png"},
        "aud": "authenticated",
        "iss": f"https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def expired_token():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "expired@example.com",
        "user_metadata": {"full_name": "Expired User"},
        "aud": "authenticated",
        "iss": f"https://test.supabase.co/auth/v1",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def rs256_token_and_jwks():
    now = datetime.now(timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_numbers = key.public_key().public_numbers()

    def to_base64url(value: int) -> str:
        as_bytes = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return base64url_encode(as_bytes).decode()

    jwk = {
        "kty": "RSA",
        "kid": "test-rs256-key",
        "use": "sig",
        "alg": "RS256",
        "n": to_base64url(public_numbers.n),
        "e": to_base64url(public_numbers.e),
    }
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "rsa-user@example.com",
        "user_metadata": {"full_name": "RSA User"},
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": jwk["kid"]},
    )
    return token, {"keys": [jwk]}


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://test.supabase.co")

    from app.core.config import Settings
    test_settings = Settings(
        SUPABASE_JWT_SECRET=TEST_SECRET,
        SUPABASE_PROJECT_URL="https://test.supabase.co",
    )
    monkeypatch.setattr("app.core.auth.settings", test_settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_protected_route_without_token(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_route_with_valid_token(client, valid_token):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"


@pytest.mark.anyio
async def test_protected_route_with_expired_token(client, expired_token):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_route_with_invalid_token(client):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token-string"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_route_with_rs256_token(client, monkeypatch, rs256_token_and_jwks):
    token, jwks = rs256_token_and_jwks

    async def fake_fetch_jwks(issuer: str):
        assert issuer == "https://test.supabase.co/auth/v1"
        return jwks["keys"]

    monkeypatch.setattr("app.core.auth._fetch_jwks", fake_fetch_jwks)

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "rsa-user@example.com"
