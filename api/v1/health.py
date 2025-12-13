"""Health check endpoint."""

from fastapi import APIRouter

import config

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status and environment information
    """
    return {
        "status": "ok",
        "env": config.settings.ENV,
    }

