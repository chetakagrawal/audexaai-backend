"""Database connectivity check endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

router = APIRouter()


@router.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)):
    """
    Check database connectivity.

    Returns:
        dict: Database status

    Raises:
        HTTPException: If database connection fails
    """
    try:
        # Test database connection with a simple query
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"db": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}",
        )

