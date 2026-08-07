import pytest
from httpx import AsyncClient
from uuid import uuid4
from app.main import app
from app.dependencies import get_current_identity, get_current_workspace_context
from app.context import CurrentIdentity, CurrentWorkspaceContext
from app.domain.workspace.models import Workspace
from app.domain.identity.models import User
from app.infrastructure.cache.redis import redis_client
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_workspace_id():
    return uuid4()

@pytest.fixture
def mock_actor_id():
    return uuid4()

@pytest.fixture
def override_auth(mock_workspace_id, mock_actor_id):
    def mock_get_current_identity():
        user = User(id=mock_actor_id, email="test@example.com", display_name="Test")
        return CurrentIdentity(request_id="test-req", correlation_id="test-corr", user=user, auth_type="jwt")

    def mock_get_current_workspace_context():
        ws = Workspace(id=mock_workspace_id, name="Test WS")
        return CurrentWorkspaceContext(workspace=ws, configuration=None, policy=None, permissions={"workspace:read"})

    app.dependency_overrides[get_current_identity] = mock_get_current_identity
    app.dependency_overrides[get_current_workspace_context] = mock_get_current_workspace_context
    yield
    app.dependency_overrides.clear()


@patch("app.api.v1.integrations.redis_client.keys", new_callable=AsyncMock)
@patch("app.api.v1.integrations.redis_client.delete", new_callable=AsyncMock)
@patch("app.api.v1.integrations.redis_client.get", new_callable=AsyncMock)
@patch("app.api.v1.integrations.redis_client.setex", new_callable=AsyncMock)
async def test_connect_integration_redirects_to_provider(mock_setex, mock_get, mock_delete, mock_keys, client: AsyncClient, override_auth, mock_workspace_id, mock_actor_id):
    mock_keys.return_value = ["integration_state:test_state"]
    mock_get.return_value = f"{mock_workspace_id}:{mock_actor_id}"

    response = await client.get(
        f"/api/v1/workspaces/{mock_workspace_id}/integrations/slack/connect",
        follow_redirects=False
    )
    
    assert response.status_code == 307
    assert "https://slack.com/oauth/v2/authorize" in response.headers["location"]
    
    mock_setex.assert_called_once()
    assert mock_setex.call_args[0][2] == f"{mock_workspace_id}:{mock_actor_id}"


@patch("app.api.v1.integrations.redis_client.delete", new_callable=AsyncMock)
@patch("app.api.v1.integrations.redis_client.get", new_callable=AsyncMock)
@patch("app.domain.identity.providers.slack.SlackLoginProvider.exchange_code", new_callable=AsyncMock)
@patch("app.domain.integrations.service.IntegrationService.connect_integration", new_callable=AsyncMock)
async def test_connect_integration_callback(
    mock_connect_integration, 
    mock_exchange, 
    mock_get,
    mock_delete,
    client: AsyncClient, 
    override_auth, 
    mock_workspace_id, 
    mock_actor_id
):
    state = "test_state_123"
    mock_get.return_value = f"{mock_workspace_id}:{mock_actor_id}"
    
    mock_exchange.return_value = {
        "access_token": "xoxb-test",
        "refresh_token": "xoxr-test"
    }

    response = await client.get(
        f"/api/v1/workspaces/integrations/slack/callback?code=testcode&state={state}",
        follow_redirects=False
    )
    
    assert response.status_code == 302
    assert f"/workspaces/{mock_workspace_id}/integrations" in response.headers["location"]
    
    mock_exchange.assert_called_once_with("testcode", f"http://localhost:8000/api/v1/workspaces/integrations/slack/callback")
    mock_connect_integration.assert_called_once()
    mock_delete.assert_called_once_with(f"integration_state:{state}")


@patch("app.domain.integrations.service.IntegrationService.get_integrations", new_callable=AsyncMock)
async def test_list_integrations(mock_get_integrations, client: AsyncClient, override_auth, mock_workspace_id):
    mock_get_integrations.return_value = []
    
    response = await client.get(f"/api/v1/workspaces/{mock_workspace_id}/integrations")
    assert response.status_code == 200
    assert response.json() == []


@patch("app.domain.integrations.service.IntegrationService.disconnect_integration", new_callable=AsyncMock)
async def test_disconnect_integration(mock_disconnect, client: AsyncClient, override_auth, mock_workspace_id):
    integration_id = uuid4()
    response = await client.delete(f"/api/v1/workspaces/{mock_workspace_id}/integrations/{integration_id}")
    
    assert response.status_code == 204
    mock_disconnect.assert_called_once_with(integration_id, mock_workspace_id)
