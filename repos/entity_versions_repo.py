"""Repository for EntityVersion database operations."""

from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.entity_version import EntityVersion


async def list_versions(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> list[EntityVersion]:
    """
    List all versions for a specific entity, ordered by version_num descending.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        entity_type: Entity type (e.g., 'controls')
        entity_id: Entity ID to fetch versions for
    
    Returns:
        List of EntityVersion records, ordered by version_num DESC
    """
    query = (
        select(EntityVersion)
        .where(
            EntityVersion.tenant_id == tenant_id,
            EntityVersion.entity_type == entity_type,
            EntityVersion.entity_id == entity_id,
        )
        .order_by(desc(EntityVersion.version_num))
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())

