import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.oauth_registry import oauth_registry
from app.credentials.manager import encrypt_token
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.integrations import Credential, Integration, WorkspaceCapability
from app.models.tenancy import Membership, User
from app.utils.redis import redis_client

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/{provider}/connect")
async def connect_integration(
    provider: str,
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate OAuth flow to link an external integration to a workspace."""
    
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
            detail="You are not a member of this workspace.",
        )

    try:
        provider_impl = oauth_registry.get_provider(provider)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    state = secrets.token_urlsafe(32)
    
    await redis_client.setex(f"integration_state:{state}", 600, f"{workspace_id}:{user.id}")

    
    redirect_uri = f"http://localhost:8000/api/integrations/{provider}/callback"
    auth_url = provider_impl.get_authorization_url(state, redirect_uri)
    return RedirectResponse(auth_url)


@router.get("/{provider}/callback")
async def connect_callback(
    provider: str,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Callback target for OAuth integration connection flows."""
    state_key = f"integration_state:{state}"
    saved_data = await redis_client.get(state_key)
    if not saved_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
    await redis_client.delete(state_key)

    workspace_id, owner_user_id = saved_data.split(":")

    try:
        provider_impl = oauth_registry.get_provider(provider)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    redirect_uri = f"http://localhost:8000/api/integrations/{provider}/callback"
    token_payload = await provider_impl.exchange_code(code, redirect_uri)
    access_token = token_payload.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth did not return an access token")

    
    encrypted_token = encrypt_token(access_token)
    encrypted_refresh = None
    if token_payload.get("refresh_token"):
         encrypted_refresh = encrypt_token(token_payload.get("refresh_token"))

    
    provider_variant = f"{provider}_cloud"

    
    result = await db.execute(
        select(Integration).filter(
            Integration.workspace_id == workspace_id,
            Integration.provider_type == provider,
        )
    )
    integration = result.scalars().first()

    if not integration:
        integration = Integration(
            workspace_id=workspace_id,
            provider_type=provider,
            provider_variant=provider_variant,
            type="WORKSPACE",
            status="CONNECTED",
        )
        db.add(integration)
        await db.flush()

    
    cred_result = await db.execute(
        select(Credential).filter(Credential.integration_id == integration.id)
    )
    credential = cred_result.scalars().first()

    if credential:
        credential.encrypted_token = encrypted_token
        credential.encrypted_refresh = encrypted_refresh
        credential.owner_user_id = owner_user_id
    else:
        credential = Credential(
            integration_id=integration.id,
            owner_user_id=owner_user_id,
            encrypted_token=encrypted_token,
            encrypted_refresh=encrypted_refresh,
        )
        db.add(credential)

    
    if provider == "github":
        
        cap_result = await db.execute(
            select(WorkspaceCapability).filter(
                WorkspaceCapability.workspace_id == workspace_id,
                WorkspaceCapability.capability == "create_issue",
            )
        )
        mapping = cap_result.scalars().first()
        if not mapping:
            mapping = WorkspaceCapability(
                workspace_id=workspace_id,
                capability="create_issue",
                integration_id=integration.id,
            )
            db.add(mapping)

    await db.commit()

    
    return RedirectResponse(f"http://localhost:3000/dashboard?integration_success={provider}")
