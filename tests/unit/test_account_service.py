"""
Unit tests for AccountService.

Tests CRUD operations and login status management with in-memory SQLite.
"""

import pytest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
from src.models.account import Account, AccountStatus
from src.models.client import Client
from src.services.account_service import AccountService


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
    return AccountService(session)


@pytest.fixture
async def sample_client(session):
    """Insert a Client row so foreign key constraints are satisfied."""
    client = Client(id="client-test001", name="Test Corp", industry="tech")
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


# ---------------------------------------------------------------------------
# create_account
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateAccount:
    """Tests for AccountService.create_account."""

    async def test_create_account_success(self, service, sample_client):
        result = await service.create_account(
            client_id=sample_client.id,
            platform="xiaohongshu",
            username="testuser",
            status=AccountStatus.ACTIVE,
        )

        assert result.success is True
        account = result.data
        assert isinstance(account, Account)
        assert account.client_id == sample_client.id
        assert account.platform == "xiaohongshu"
        assert account.username == "testuser"
        assert account.status == AccountStatus.ACTIVE
        assert account.is_logged_in is False
        assert account.id is not None

    async def test_create_account_default_status(self, service, sample_client):
        """Default status should be ACTIVE."""
        result = await service.create_account(
            client_id=sample_client.id,
            platform="weibo",
            username="weibouser",
        )

        assert result.success is True
        assert result.data.status == AccountStatus.ACTIVE

    async def test_create_account_inactive_status(self, service, sample_client):
        result = await service.create_account(
            client_id=sample_client.id,
            platform="zhihu",
            username="zhihuuser",
            status=AccountStatus.INACTIVE,
        )

        assert result.success is True
        assert result.data.status == AccountStatus.INACTIVE

    async def test_create_account_exception(self, session, sample_client):
        svc = AccountService(session)

        async def _boom():
            raise RuntimeError("DB error")
        session.commit = _boom

        result = await svc.create_account(
            client_id=sample_client.id,
            platform="weibo",
            username="user",
        )

        assert result.success is False
        assert result.error_code == "ACCOUNT_CREATE_ERROR"


# ---------------------------------------------------------------------------
# get_account
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAccount:
    """Tests for AccountService.get_account."""

    async def test_get_account_success(self, service, sample_client):
        create_result = await service.create_account(
            client_id=sample_client.id,
            platform="xiaohongshu",
            username="testuser",
        )
        account_id = create_result.data.id

        result = await service.get_account(account_id)

        assert result.success is True
        assert result.data.id == account_id
        assert result.data.username == "testuser"

    async def test_get_account_not_found(self, service):
        result = await service.get_account("nonexistent-id")

        assert result.success is False
        assert result.error_code == "ACCOUNT_NOT_FOUND"

    async def test_get_account_exception(self, session):
        svc = AccountService(session)

        async def _boom(*args, **kwargs):
            raise RuntimeError("DB error")
        session.execute = _boom

        result = await svc.get_account("any-id")

        assert result.success is False
        assert result.error_code == "ACCOUNT_GET_ERROR"


# ---------------------------------------------------------------------------
# list_accounts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListAccounts:
    """Tests for AccountService.list_accounts."""

    async def test_list_all_accounts(self, service, sample_client):
        for i in range(3):
            await service.create_account(
                client_id=sample_client.id,
                platform="xiaohongshu",
                username=f"user{i}",
            )

        result = await service.list_accounts()

        assert result.success is True
        assert len(result.data) == 3

    async def test_list_accounts_filter_by_client_id(self, service, session):
        # Create two clients
        c1 = Client(id="client-aaa", name="Corp A")
        c2 = Client(id="client-bbb", name="Corp B")
        session.add_all([c1, c2])
        await session.commit()

        await service.create_account(client_id="client-aaa", platform="weibo", username="u1")
        await service.create_account(client_id="client-aaa", platform="weibo", username="u2")
        await service.create_account(client_id="client-bbb", platform="weibo", username="u3")

        result = await service.list_accounts(client_id="client-aaa")

        assert result.success is True
        assert len(result.data) == 2

    async def test_list_accounts_filter_by_platform(self, service, sample_client):
        await service.create_account(
            client_id=sample_client.id, platform="xiaohongshu", username="u1"
        )
        await service.create_account(
            client_id=sample_client.id, platform="weibo", username="u2"
        )

        result = await service.list_accounts(platform="weibo")

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].platform == "weibo"

    async def test_list_accounts_with_skip_limit(self, service, sample_client):
        for i in range(5):
            await service.create_account(
                client_id=sample_client.id, platform="weibo", username=f"u{i}"
            )

        result = await service.list_accounts(skip=2, limit=2)

        assert result.success is True
        assert len(result.data) == 2

    async def test_list_accounts_empty(self, service):
        result = await service.list_accounts()

        assert result.success is True
        assert result.data == []

    async def test_list_accounts_exception(self, session):
        svc = AccountService(session)

        async def _boom(*args, **kwargs):
            raise RuntimeError("DB error")
        session.execute = _boom

        result = await svc.list_accounts()

        assert result.success is False
        assert result.error_code == "ACCOUNT_LIST_ERROR"


# ---------------------------------------------------------------------------
# update_account
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateAccount:
    """Tests for AccountService.update_account."""

    async def test_update_account_success(self, service, sample_client):
        create_result = await service.create_account(
            client_id=sample_client.id,
            platform="xiaohongshu",
            username="oldname",
        )
        account_id = create_result.data.id

        result = await service.update_account(
            account_id, username="newname", status=AccountStatus.SUSPENDED
        )

        assert result.success is True
        assert result.data.username == "newname"
        assert result.data.status == AccountStatus.SUSPENDED

    async def test_update_account_not_found(self, service):
        result = await service.update_account("nonexistent-id", username="x")

        assert result.success is False
        assert result.error_code == "ACCOUNT_NOT_FOUND"

    async def test_update_account_ignores_unknown_fields(self, service, sample_client):
        create_result = await service.create_account(
            client_id=sample_client.id, platform="weibo", username="u1"
        )
        account_id = create_result.data.id

        result = await service.update_account(account_id, nonexistent_field="value")

        assert result.success is True
        assert result.data.username == "u1"  # unchanged

    async def test_update_account_exception(self, session, sample_client):
        svc = AccountService(session)
        create_result = await svc.create_account(
            client_id=sample_client.id, platform="weibo", username="u1"
        )
        aid = create_result.data.id

        async def _boom():
            raise RuntimeError("DB error")
        session.commit = _boom

        result = await svc.update_account(aid, username="new")

        assert result.success is False
        assert result.error_code == "ACCOUNT_UPDATE_ERROR"


# ---------------------------------------------------------------------------
# delete_account
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeleteAccount:
    """Tests for AccountService.delete_account."""

    async def test_delete_account_success(self, service, sample_client):
        create_result = await service.create_account(
            client_id=sample_client.id, platform="weibo", username="u1"
        )
        account_id = create_result.data.id

        result = await service.delete_account(account_id)

        assert result.success is True
        assert result.data is None

        # Verify it's gone
        get_result = await service.get_account(account_id)
        assert get_result.success is False
        assert get_result.error_code == "ACCOUNT_NOT_FOUND"

    async def test_delete_account_not_found(self, service):
        result = await service.delete_account("nonexistent-id")

        assert result.success is False
        assert result.error_code == "ACCOUNT_NOT_FOUND"

    async def test_delete_account_exception(self, session, sample_client):
        svc = AccountService(session)
        create_result = await svc.create_account(
            client_id=sample_client.id, platform="weibo", username="u1"
        )
        aid = create_result.data.id

        # Patch delete to raise
        original_delete = session.delete
        async def _boom(obj):
            raise RuntimeError("DB error")
        session.delete = _boom

        result = await svc.delete_account(aid)

        assert result.success is False
        assert result.error_code == "ACCOUNT_DELETE_ERROR"

        session.delete = original_delete


# ---------------------------------------------------------------------------
# update_login_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateLoginStatus:
    """Tests for AccountService.update_login_status."""

    async def test_login_sets_is_logged_in_and_last_login(self, service, sample_client):
        create_result = await service.create_account(
            client_id=sample_client.id, platform="xiaohongshu", username="u1"
        )
        account_id = create_result.data.id

        result = await service.update_login_status(account_id, is_logged_in=True)

        assert result.success is True
        assert result.data.is_logged_in is True
        assert result.data.last_login is not None

    async def test_logout_clears_is_logged_in(self, service, sample_client):
        create_result = await service.create_account(
            client_id=sample_client.id, platform="xiaohongshu", username="u1"
        )
        account_id = create_result.data.id

        # Login first
        await service.update_login_status(account_id, is_logged_in=True)
        # Then logout
        result = await service.update_login_status(account_id, is_logged_in=False)

        assert result.success is True
        assert result.data.is_logged_in is False

    async def test_update_login_status_not_found(self, service):
        result = await service.update_login_status("nonexistent-id", is_logged_in=True)

        assert result.success is False
        assert result.error_code == "ACCOUNT_NOT_FOUND"

    async def test_update_login_status_exception(self, session, sample_client):
        svc = AccountService(session)
        create_result = await svc.create_account(
            client_id=sample_client.id, platform="weibo", username="u1"
        )
        aid = create_result.data.id

        async def _boom():
            raise RuntimeError("DB error")
        session.commit = _boom

        result = await svc.update_login_status(aid, is_logged_in=True)

        assert result.success is False
        assert result.error_code == "ACCOUNT_UPDATE_ERROR"
