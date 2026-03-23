"""Account management routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.schemas.account import AccountCreate, AccountUpdate
from src.services.account_service import AccountService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("/", status_code=201)
async def create_account(
    account: AccountCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new account."""
    service = AccountService(db)
    result = await service.create_account(
        client_id=account.client_id,
        platform=account.platform.value,
        username=account.username,
        status=account.status.value,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    a = result.data
    return {
        "success": True,
        "data": {
            "id": a.id,
            "client_id": a.client_id,
            "platform": a.platform,
            "username": a.username,
            "status": a.status,
            "is_logged_in": a.is_logged_in,
            "last_login": a.last_login.isoformat() if a.last_login else None,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        },
    }


@router.get("/")
async def list_accounts(
    client_id: str | None = None,
    platform: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List accounts with optional filters."""
    service = AccountService(db)
    result = await service.list_accounts(
        client_id=client_id,
        platform=platform,
        skip=skip,
        limit=limit,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    items = [
        {
            "id": a.id,
            "client_id": a.client_id,
            "platform": a.platform,
            "username": a.username,
            "status": a.status,
            "is_logged_in": a.is_logged_in,
            "last_login": a.last_login.isoformat() if a.last_login else None,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        }
        for a in result.data
    ]
    return {
        "success": True,
        "data": {"items": items, "total": len(items)},
    }


@router.get("/{account_id}")
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get account details."""
    service = AccountService(db)
    result = await service.get_account(account_id)

    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)

    a = result.data
    return {
        "success": True,
        "data": {
            "id": a.id,
            "client_id": a.client_id,
            "platform": a.platform,
            "username": a.username,
            "status": a.status,
            "is_logged_in": a.is_logged_in,
            "last_login": a.last_login.isoformat() if a.last_login else None,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        },
    }


@router.put("/{account_id}")
async def update_account(
    account_id: str,
    account_update: AccountUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update account."""
    service = AccountService(db)
    update_data = {}
    for key, value in account_update.model_dump(exclude_unset=True).items():
        if hasattr(value, "value"):
            update_data[key] = value.value
        else:
            update_data[key] = value

    result = await service.update_account(account_id, **update_data)

    if not result.success:
        if "不存在" in (result.error or ""):
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    a = result.data
    return {
        "success": True,
        "data": {
            "id": a.id,
            "client_id": a.client_id,
            "platform": a.platform,
            "username": a.username,
            "status": a.status,
            "is_logged_in": a.is_logged_in,
            "last_login": a.last_login.isoformat() if a.last_login else None,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        },
    }


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete account."""
    service = AccountService(db)
    result = await service.delete_account(account_id)

    if not result.success:
        if "不存在" in (result.error or ""):
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)
