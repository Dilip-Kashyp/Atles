from typing import Any

from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.auth.jwt import verify_token
from app.database.session import get_db
from app.models.tenancy import User, Membership, Workspace
from app.orchestrator.agent import Orchestrator
from app.orchestrator.platform_base import ChatPlatform

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency to extract the current authenticated user via JWT or query token."""
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(token, expected_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_workspace_membership(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Membership:
    """Ensure the user belongs to the requested workspace and return their membership."""
    result = await db.execute(
        select(Membership).filter(
            Membership.user_id == user.id,
            Membership.workspace_id == workspace_id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    return membership


def get_orchestrator(request: Request) -> Orchestrator:
    """Resolve the orchestrator from FastAPI app state."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator is not configured")
    return orchestrator


def get_slack_platform(request: Request) -> ChatPlatform:
    """Resolve the Slack platform adapter from FastAPI app state."""
    platform = getattr(request.app.state, "slack_platform", None)
    if platform is None:
        raise HTTPException(status_code=500, detail="Slack platform is not configured")
    return platform
