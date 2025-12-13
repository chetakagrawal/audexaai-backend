"""Quick script to check database records."""

import asyncio
import sys
import selectors
from sqlalchemy import select
from db import AsyncSessionLocal
from models.tenant import Tenant
from models.user import User


async def check_db():
    async with AsyncSessionLocal() as db:
        # Get tenants
        tenants_result = await db.execute(select(Tenant))
        tenants = tenants_result.scalars().all()
        
        # Get users
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()
        
        print("=" * 50)
        print("DATABASE RECORDS")
        print("=" * 50)
        
        print(f"\nTenants: {len(tenants)}")
        for t in tenants:
            print(f"  - {t.name}")
            print(f"    Slug: {t.slug}")
            print(f"    ID: {t.id}")
            print(f"    Status: {t.status}")
            print()
        
        print(f"Users: {len(users)}")
        for u in users:
            print(f"   • {u.email}")
            print(f"     Name: {u.name}")
            print(f"     Role: {u.role}")
            print(f"     Tenant ID: {u.tenant_id}")
            print(f"     Active: {u.is_active}")
            print()


if __name__ == "__main__":
    # Fix for Windows asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_db())

