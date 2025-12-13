"""Main API router that includes versioned routers."""

from fastapi import APIRouter

from api.v1 import auth, controls, db_check, health, me_stub, projects, tenants, users

# Main API router
api_router = APIRouter()

# Include v1 routers
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(auth.router, tags=["auth"])
v1_router.include_router(me_stub.router, tags=["users"])
v1_router.include_router(db_check.router, tags=["database"])
v1_router.include_router(tenants.router, tags=["tenants"])
v1_router.include_router(users.router, tags=["users"])
v1_router.include_router(projects.router, tags=["projects"])
v1_router.include_router(controls.router, tags=["controls"])

api_router.include_router(v1_router)

