"""Client management routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.schemas.client import ClientCreate, ClientUpdate
from src.services.client_service import ClientService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", status_code=201)
async def create_client(
    client: ClientCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new client."""
    service = ClientService(db)
    result = await service.create_client(
        name=client.name,
        industry=client.industry,
        description=client.description,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    c = result.data
    return {
        "success": True,
        "data": {
            "id": c.id,
            "name": c.name,
            "industry": c.industry,
            "description": c.description,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        },
    }


@router.get("/")
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all clients."""
    service = ClientService(db)
    result = await service.list_clients(skip=skip, limit=limit)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    items = [
        {
            "id": c.id,
            "name": c.name,
            "industry": c.industry,
            "description": c.description,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in result.data
    ]
    return {
        "success": True,
        "data": {"items": items, "total": len(items)},
    }


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get client details."""
    service = ClientService(db)
    result = await service.get_client(client_id)

    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)

    c = result.data
    return {
        "success": True,
        "data": {
            "id": c.id,
            "name": c.name,
            "industry": c.industry,
            "description": c.description,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        },
    }


@router.put("/{client_id}")
async def update_client(
    client_id: str,
    client_update: ClientUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update client."""
    service = ClientService(db)
    update_data = client_update.model_dump(exclude_unset=True)
    result = await service.update_client(client_id, **update_data)

    if not result.success:
        if "不存在" in (result.error or ""):
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=400, detail=result.error)

    c = result.data
    return {
        "success": True,
        "data": {
            "id": c.id,
            "name": c.name,
            "industry": c.industry,
            "description": c.description,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        },
    }


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete client."""
    service = ClientService(db)
    result = await service.delete_client(client_id)

    if not result.success:
        if "不存在" in (result.error or ""):
            raise HTTPException(status_code=404, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)
