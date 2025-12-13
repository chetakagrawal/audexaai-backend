"""Tenant endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tenant import Tenant, TenantResponse
from db import get_db

router = APIRouter()


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    """
    List all tenants.
    
    Returns:
        List of all tenants in the system.
    """
    try:
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        return tenants
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tenants: {str(e)}",
        )

