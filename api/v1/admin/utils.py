"""Utility functions for admin endpoints."""

import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.tenant import Tenant


def generate_slug(name: str) -> str:
    """
    Generate a URL-safe slug from a name.
    
    Args:
        name: Company or workspace name
    
    Returns:
        URL-safe slug (lowercase, hyphens, alphanumeric)
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[_\s]+', '-', slug)
    # Remove all non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Fallback if empty
    if not slug:
        slug = "workspace"
    return slug


async def ensure_unique_slug(
    db: AsyncSession,
    base_slug: str,
    max_attempts: int = 100,
) -> str:
    """
    Ensure a tenant slug is unique by appending a suffix if needed.
    
    Args:
        db: Database session
        base_slug: Base slug to make unique
        max_attempts: Maximum number of attempts before failing
    
    Returns:
        Unique slug
    """
    slug = base_slug
    
    for attempt in range(max_attempts):
        # Check if slug exists
        result = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            return slug
        
        # Append suffix
        if attempt == 0:
            slug = f"{base_slug}-1"
        else:
            # Extract number and increment
            match = re.search(r'-(\d+)$', slug)
            if match:
                num = int(match.group(1))
                slug = f"{base_slug}-{num + 1}"
            else:
                slug = f"{base_slug}-{attempt + 1}"
    
    raise ValueError(f"Could not generate unique slug after {max_attempts} attempts")
