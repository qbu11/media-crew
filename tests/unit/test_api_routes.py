"""
Tests for API routes: clients, accounts, images, research.

Uses FastAPI TestClient with overridden get_db dependency.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base


@pytest.fixture
async def db_engine():
    """In-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Async session for testing."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def app(db_engine):
    """FastAPI app with overridden database dependency."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from src.api.dependencies import get_db
    from src.api.routes import accounts, clients, images, research

    application = FastAPI()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(clients.router, prefix="/api")
    application.include_router(accounts.router, prefix="/api")
    application.include_router(images.router, prefix="/api")
    application.include_router(research.router, prefix="/api")

    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture
async def client(app):
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============ Client Routes ============

class TestClientRoutes:
    async def test_create_client(self, client):
        resp = await client.post("/api/clients/", json={
            "name": "Test Client",
            "industry": "Tech",
            "description": "A test client",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Client"

    async def test_list_clients_empty(self, client):
        resp = await client.get("/api/clients/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0

    async def test_list_clients_with_data(self, client):
        await client.post("/api/clients/", json={"name": "Client A"})
        await client.post("/api/clients/", json={"name": "Client B"})
        resp = await client.get("/api/clients/")
        assert resp.json()["data"]["total"] == 2

    async def test_get_client(self, client):
        create_resp = await client.post("/api/clients/", json={"name": "Test Client"})
        client_id = create_resp.json()["data"]["id"]

        resp = await client.get(f"/api/clients/{client_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Test Client"

    async def test_get_client_not_found(self, client):
        resp = await client.get("/api/clients/nonexistent-id")
        assert resp.status_code == 404

    async def test_update_client(self, client):
        create_resp = await client.post("/api/clients/", json={"name": "Old Name"})
        client_id = create_resp.json()["data"]["id"]

        resp = await client.put(f"/api/clients/{client_id}", json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New Name"

    async def test_update_client_not_found(self, client):
        resp = await client.put("/api/clients/nonexistent-id", json={"name": "Name"})
        assert resp.status_code == 404

    async def test_delete_client(self, client):
        create_resp = await client.post("/api/clients/", json={"name": "To Delete"})
        client_id = create_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/clients/{client_id}")
        assert resp.status_code == 204

        # Verify deleted
        resp = await client.get(f"/api/clients/{client_id}")
        assert resp.status_code == 404

    async def test_delete_client_not_found(self, client):
        resp = await client.delete("/api/clients/nonexistent-id")
        assert resp.status_code == 404


# ============ Account Routes ============

class TestAccountRoutes:
    async def _create_client(self, client):
        resp = await client.post("/api/clients/", json={"name": "Test Client"})
        return resp.json()["data"]["id"]

    async def test_create_account(self, client):
        client_id = await self._create_client(client)
        resp = await client.post("/api/accounts/", json={
            "client_id": client_id,
            "platform": "xiaohongshu",
            "username": "testuser",
            "status": "active",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["username"] == "testuser"

    async def test_list_accounts_empty(self, client):
        resp = await client.get("/api/accounts/")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0

    async def test_list_accounts_with_filter(self, client):
        client_id = await self._create_client(client)
        await client.post("/api/accounts/", json={
            "client_id": client_id, "platform": "xiaohongshu", "username": "user1"
        })
        await client.post("/api/accounts/", json={
            "client_id": client_id, "platform": "weibo", "username": "user2"
        })

        resp = await client.get("/api/accounts/?platform=xiaohongshu")
        assert resp.json()["data"]["total"] == 1

    async def test_get_account(self, client):
        client_id = await self._create_client(client)
        create_resp = await client.post("/api/accounts/", json={
            "client_id": client_id, "platform": "weibo", "username": "test"
        })
        account_id = create_resp.json()["data"]["id"]

        resp = await client.get(f"/api/accounts/{account_id}")
        assert resp.status_code == 200

    async def test_get_account_not_found(self, client):
        resp = await client.get("/api/accounts/nonexistent-id")
        assert resp.status_code == 404

    async def test_update_account(self, client):
        client_id = await self._create_client(client)
        create_resp = await client.post("/api/accounts/", json={
            "client_id": client_id, "platform": "zhihu", "username": "old"
        })
        account_id = create_resp.json()["data"]["id"]

        resp = await client.put(f"/api/accounts/{account_id}", json={
            "username": "new_name"
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "new_name"

    async def test_update_account_not_found(self, client):
        resp = await client.put("/api/accounts/nonexistent-id", json={"username": "x"})
        assert resp.status_code == 404

    async def test_delete_account(self, client):
        client_id = await self._create_client(client)
        create_resp = await client.post("/api/accounts/", json={
            "client_id": client_id, "platform": "bilibili", "username": "delete_me"
        })
        account_id = create_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/accounts/{account_id}")
        assert resp.status_code == 204

    async def test_delete_account_not_found(self, client):
        resp = await client.delete("/api/accounts/nonexistent-id")
        assert resp.status_code == 404


# ============ Image Routes ============

class TestImageRoutes:
    async def test_list_platforms(self, client):
        resp = await client.get("/api/images/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "xiaohongshu" in data["data"]

    async def test_list_color_schemes(self, client):
        resp = await client.get("/api/images/color-schemes")
        assert resp.status_code == 200
        data = resp.json()
        assert "tech" in data["data"]
        assert "business" in data["data"]

    async def test_generate_images(self, client):
        resp = await client.post("/api/images/generate", json={
            "platform": "xiaohongshu",
            "color_scheme": "tech",
            "content": {"title": "Test Title", "tags": ["t1"]},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["count"] >= 1

    async def test_generate_single_cover(self, client):
        resp = await client.post("/api/images/generate-single", json={
            "platform": "weibo",
            "image_type": "cover",
            "data": {"title": "Cover Title"},
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_generate_single_comparison(self, client):
        resp = await client.post("/api/images/generate-single", json={
            "platform": "zhihu",
            "image_type": "comparison",
            "data": {"title": "Compare", "headers": ["A", "B"], "rows": [["1", "2"]]},
        })
        assert resp.status_code == 200

    async def test_generate_single_highlights(self, client):
        resp = await client.post("/api/images/generate-single", json={
            "platform": "xiaohongshu",
            "image_type": "highlights",
            "data": {"title": "HL", "items": [{"title": "H1", "desc1": "D1", "desc2": "D2"}]},
        })
        assert resp.status_code == 200

    async def test_generate_single_summary(self, client):
        resp = await client.post("/api/images/generate-single", json={
            "platform": "douyin",
            "image_type": "summary",
            "data": {"title": "Sum", "items": [["S", "M", "R"]]},
        })
        assert resp.status_code == 200

    async def test_list_history(self, client):
        resp = await client.get("/api/images/history")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ============ Research Routes ============

class TestResearchRoutes:
    async def test_research_status(self, client):
        resp = await client.get("/api/research/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "wechat_search" in data
        assert "wechat_spider" in data
