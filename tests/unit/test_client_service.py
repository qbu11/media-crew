"""
Unit tests for ClientService.

Tests CRUD operations with in-memory SQLite.
"""

import pytest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.client import Client
from src.services.client_service import ClientService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture
def service(session):
    return ClientService(session)


# ---------------------------------------------------------------------------
# create_client
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateClient:
    """Tests for ClientService.create_client."""

    async def test_create_client_success(self, service):
        result = await service.create_client(
            name="Acme Corp",
            industry="technology",
            description="A tech company",
        )

        assert result.success is True
        client = result.data
        assert isinstance(client, Client)
        assert client.name == "Acme Corp"
        assert client.industry == "technology"
        assert client.description == "A tech company"
        assert client.id is not None

    async def test_create_client_minimal(self, service):
        """Only name is required."""
        result = await service.create_client(name="MinimalCorp")

        assert result.success is True
        assert result.data.name == "MinimalCorp"
        assert result.data.industry is None
        assert result.data.description is None

    async def test_create_client_duplicate_name(self, service):
        """Duplicate names should return an error."""
        await service.create_client(name="UniqueName")
        result = await service.create_client(name="UniqueName")

        assert result.success is False
        assert result.error_code == "CLIENT_NAME_EXISTS"

    async def test_create_client_exception(self, session):
        svc = ClientService(session)

        async def _boom():
            raise RuntimeError("DB error")
        session.commit = _boom

        result = await svc.create_client(name="Test")

        assert result.success is False
        assert result.error_code == "CLIENT_CREATE_ERROR"


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetClient:
    """Tests for ClientService.get_client."""

    async def test_get_client_success(self, service):
        create_result = await service.create_client(name="LookupCorp")
        client_id = create_result.data.id

        result = await service.get_client(client_id)

        assert result.success is True
        assert result.data.id == client_id
        assert result.data.name == "LookupCorp"

    async def test_get_client_not_found(self, service):
        result = await service.get_client("nonexistent-id")

        assert result.success is False
        assert result.error_code == "CLIENT_NOT_FOUND"

    async def test_get_client_exception(self, session):
        svc = ClientService(session)

        async def _boom(*args, **kwargs):
            raise RuntimeError("DB error")
        session.execute = _boom

        result = await svc.get_client("any-id")

        assert result.success is False
        assert result.error_code == "CLIENT_GET_ERROR"


# ---------------------------------------------------------------------------
# list_clients
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListClients:
    """Tests for ClientService.list_clients."""

    async def test_list_clients_returns_all(self, service):
        await service.create_client(name="A Corp")
        await service.create_client(name="B Corp")
        await service.create_client(name="C Corp")

        result = await service.list_clients()

        assert result.success is True
        assert len(result.data) == 3

    async def test_list_clients_with_skip_limit(self, service):
        for i in range(5):
            await service.create_client(name=f"Corp {i}")

        result = await service.list_clients(skip=1, limit=2)

        assert result.success is True
        assert len(result.data) == 2

    async def test_list_clients_empty(self, service):
        result = await service.list_clients()

        assert result.success is True
        assert result.data == []

    async def test_list_clients_exception(self, session):
        svc = ClientService(session)

        async def _boom(*args, **kwargs):
            raise RuntimeError("DB error")
        session.execute = _boom

        result = await svc.list_clients()

        assert result.success is False
        assert result.error_code == "CLIENT_LIST_ERROR"


# ---------------------------------------------------------------------------
# update_client
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateClient:
    """Tests for ClientService.update_client."""

    async def test_update_client_success(self, service):
        create_result = await service.create_client(
            name="OldName", industry="finance"
        )
        client_id = create_result.data.id

        result = await service.update_client(
            client_id, name="NewName", industry="tech", description="Updated"
        )

        assert result.success is True
        assert result.data.name == "NewName"
        assert result.data.industry == "tech"
        assert result.data.description == "Updated"

    async def test_update_client_not_found(self, service):
        result = await service.update_client("nonexistent-id", name="X")

        assert result.success is False
        assert result.error_code == "CLIENT_NOT_FOUND"

    async def test_update_client_ignores_unknown_fields(self, service):
        create_result = await service.create_client(name="StableCorp")
        client_id = create_result.data.id

        result = await service.update_client(client_id, bogus_field="ignored")

        assert result.success is True
        assert result.data.name == "StableCorp"  # unchanged

    async def test_update_client_partial_update(self, service):
        """Update only one field; the rest remain unchanged."""
        create_result = await service.create_client(
            name="PartialCorp", industry="edu", description="Original"
        )
        client_id = create_result.data.id

        result = await service.update_client(client_id, industry="health")

        assert result.success is True
        assert result.data.industry == "health"
        assert result.data.description == "Original"  # unchanged

    async def test_update_client_exception(self, session):
        svc = ClientService(session)
        create_result = await svc.create_client(name="ErrorCorp")
        cid = create_result.data.id

        async def _boom():
            raise RuntimeError("DB error")
        session.commit = _boom

        result = await svc.update_client(cid, name="New")

        assert result.success is False
        assert result.error_code == "CLIENT_UPDATE_ERROR"


# ---------------------------------------------------------------------------
# delete_client
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeleteClient:
    """Tests for ClientService.delete_client."""

    async def test_delete_client_success(self, service):
        create_result = await service.create_client(name="ToDeleteCorp")
        client_id = create_result.data.id

        result = await service.delete_client(client_id)

        assert result.success is True
        assert result.data is None

        # Verify it's gone
        get_result = await service.get_client(client_id)
        assert get_result.success is False
        assert get_result.error_code == "CLIENT_NOT_FOUND"

    async def test_delete_client_not_found(self, service):
        result = await service.delete_client("nonexistent-id")

        assert result.success is False
        assert result.error_code == "CLIENT_NOT_FOUND"

    async def test_delete_client_exception(self, session):
        svc = ClientService(session)
        create_result = await svc.create_client(name="ErrorCorp2")
        cid = create_result.data.id

        original_delete = session.delete
        async def _boom(obj):
            raise RuntimeError("DB error")
        session.delete = _boom

        result = await svc.delete_client(cid)

        assert result.success is False
        assert result.error_code == "CLIENT_DELETE_ERROR"

        session.delete = original_delete
