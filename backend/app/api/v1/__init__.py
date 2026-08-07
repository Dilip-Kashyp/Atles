"""API v1 Package."""
from fastapi import APIRouter

from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.auth import router as auth_router
from app.api.v1.members import router as members_router
from app.api.v1.organizations import router as orgs_router
from app.api.v1.service_accounts import router as service_accounts_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.webhooks import router as webhooks_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_router)
v1_router.include_router(orgs_router)
v1_router.include_router(workspaces_router)
v1_router.include_router(members_router)
v1_router.include_router(service_accounts_router)
v1_router.include_router(api_keys_router)
v1_router.include_router(integrations_router)
v1_router.include_router(webhooks_router)

__all__ = ["v1_router"]
