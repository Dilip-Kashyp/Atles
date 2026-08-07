# Integrations & Model Context Protocol (MCP)

Atlas leverages decoupled provider implementations and tool dispatching to execute actions against external services like Slack, GitHub, Jira, and Notion.

---

## 1. Multi-Tenant Integrations Architecture

Integrations are stored per workspace in the PostgreSQL database:
- **`Integration`**: Stores connection status, provider type (`slack`, `github`, `notion`), provider variant, and external team/workspace IDs (`provider_workspace_id`).
- **`Credential`**: Stores Fernet-encrypted access and refresh tokens.

When an action or event arrives:
1. The backend looks up the active `Integration` for the workspace.
2. `CredentialManager` decrypts the access token symmetrically.
3. The provider/tool receives the token dynamically to execute the requested operation.

---

## 2. Adding New Integration Tools

To add a new tool (e.g. Jira Issue Search):

1. Define a tool class inheriting from `BaseTool` in `backend/app/tools/`:
   ```python
   from app.tools.base import BaseTool

   class JiraSearchTool(BaseTool):
       name = "jira_search"
       description = "Search Jira issues by query."
       input_schema = {
           "type": "object",
           "properties": {
               "query": {"type": "string"}
           },
           "required": ["query"]
       }

       async def execute(self, arguments: dict) -> str:
           # Tool logic here
           return "Results..."
   ```

2. Register the tool with `ToolDispatcher` in `backend/app/main.py`.
3. The Gemini Orchestrator automatically receives the tool schema and can invoke it via function calling!
