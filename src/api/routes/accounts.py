"""Account management routes."""

from typing import Any

from fastapi import APIRouter, HTTPException

from src.schemas.account import AccountCreate, AccountUpdate, AccountResponse

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("/", status_code=201)
async def create_account(account: AccountCreate) -> dict[str, Any]:
    """Create a new account."""
    # TODO: Implement database operation
    return {
        "success": True,
        "data": {
            "id": "account-placeholder",
            **account.model_dump(),
            "is_logged_in": False,
            "last_login": None,
            "created_at": "2026-03-23T00:00:00Z",
            "updated_at": "2026-03-23T00:00:00Z",
        },
    }


@router.get("/")
async def list_accounts(
    client_id: str | None = None,
    platform: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """List accounts with optional filters."""
    # TODO: Implement database query with filters
    return {"success": True, "data": {"items": [], "total": 0}}


@router.get("/{account_id}")
async def get_account(account_id: str) -> dict[str, Any]:
    """Get account details."""
    # TODO: Implement database query
    # Example 404 handling:
    # raise HTTPException(status_code=404, detail="账号不存在")
    return {
        "success": True,
        "data": {
            "id": account_id,
            "client_id": "client-example",
            "platform": "xiaohongshu",
            "username": "示例用户",
            "status": "active",
            "is_logged_in": False,
            "last_login": None,
            "created_at": "2026-03-23T00:00:00Z",
            "updated_at": "2026-03-23T00:00:00Z",
        },
    }


@router.put("/{account_id}")
async def update_account(account_id: str, account_update: AccountUpdate) -> dict[str, Any]:
    """Update account."""
    # TODO: Implement database update
    return {
        "success": True,
        "data": {
            "id": account_id,
            **account_update.model_dump(exclude_unset=True),
            "created_at": "2026-03-23T00:00:00Z",
            "updated_at": "2026-03-23T00:00:00Z",
        },
    }


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: str) -> None:
    """Delete account."""
    # TODO: Implement database deletion
    pass
