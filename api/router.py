"""Main API router that includes versioned routers."""

from fastapi import APIRouter

from api.v1 import auth, controls, db_check, health, me_stub, project_controls, projects, setup, signups, tenants, users, applications, control_applications, test_attributes, pbc_requests, pbc, samples, evidence_files, project_test_attribute_overrides
from api.v1.admin import signups as admin_signups

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
v1_router.include_router(project_controls.router, tags=["project-controls"])
v1_router.include_router(applications.router, tags=["applications"])
v1_router.include_router(control_applications.router, tags=["control-applications"])
v1_router.include_router(test_attributes.router, tags=["test-attributes"])
v1_router.include_router(project_test_attribute_overrides.router, tags=["project-test-attribute-overrides"])
v1_router.include_router(pbc_requests.router, tags=["pbc-requests"])
v1_router.include_router(pbc.router, tags=["pbc-v2"])
v1_router.include_router(samples.router, tags=["samples"])
v1_router.include_router(evidence_files.router, tags=["evidence-files"])
v1_router.include_router(signups.router, tags=["signups"])
v1_router.include_router(setup.router, tags=["setup"])
v1_router.include_router(admin_signups.router, tags=["admin"])

api_router.include_router(v1_router)

