# Atlas MVP Architecture

Atlas is an AI delivery copilot that turns engineering conversations into structured work. The core responsibility is understanding conversations; integrations such as GitHub, Jira, and Notion are execution plugins.

## 1. Architecture principles

- Use a modular monolith, not microservices.
- Keep modules loosely coupled and easy to extract later.
- Keep the AI layer focused on reasoning, planning, and formatting.
- Keep provider execution separate from the AI layer.
- Keep authentication, credentials, and database access generic and reusable.

## 2. High-level architecture

```text
Communication Platforms
  Slack / Teams / Discord
        ↓
  Webhook + Event Ingestion
        ↓
  API Layer
        ↓
  Conversation Pipeline
        ↓
  LangGraph / Planner
        ↓
  Tool Dispatcher
        ↓
  Credential Manager
        ↓
  Provider Layer
        ↓
  GitHub / Jira / Notion
```

### Core modules

- backend/api: HTTP routes and request validation
- backend/auth: JWT, OAuth, session handling
- backend/dashboard: dashboard-oriented endpoints and account management
- backend/ai: LangGraph orchestration, prompts, state, planners, extractors
- backend/dispatcher: selects the correct provider and executes the action
- backend/providers: GitHub, Jira, Notion implementations
- backend/credentials: encryption and secret handling
- backend/database: SQLAlchemy session and migrations
- backend/models: domain models
- backend/services: reusable business logic
- backend/utils: shared helpers

## 3. Recommended folder structure

```text
backend/
  api/
    auth.py
    dashboard.py
    integrations.py
    slack.py
    webhooks.py
  auth/
    jwt.py
    oauth_registry.py
    providers.py
  ai/
    graph.py
    planner.py
    extractor.py
    summarizer.py
    formatter.py
    prompts.py
    state.py
  dispatcher/
    dispatcher.py
    registry.py
  providers/
    github.py
    jira.py
    notion.py
    base.py
  credentials/
    manager.py
  database/
    session.py
    migrations/
  models/
    organizations.py
    users.py
    memberships.py
    integrations.py
    conversations.py
    messages.py
    action_items.py
    tool_invocations.py
  services/
    conversation_service.py
    integration_service.py
    action_service.py
  utils/
    response_formatter.py
    redis.py
frontend/
  src/app/
  src/components/
  src/lib/
```

## 4. Database schema

### Core tables

- organizations
  - id
  - name
  - slug
  - created_at
- users
  - id
  - email
  - name
  - avatar_url
  - created_at
- memberships
  - id
  - organization_id
  - user_id
  - role
  - created_at
- integrations
  - id
  - organization_id
  - workspace_id
  - provider_type
  - provider_variant
  - status
  - created_at
- credentials
  - id
  - integration_id
  - owner_user_id
  - encrypted_token
  - encrypted_refresh
  - expires_at
  - created_at
- conversations
  - id
  - organization_id
  - platform
  - external_thread_id
  - channel_id
  - title
  - created_at
- messages
  - id
  - conversation_id
  - external_message_id
  - author_id
  - content
  - created_at
  - metadata_json
- action_items
  - id
  - conversation_id
  - title
  - description
  - priority
  - status
  - owner_user_id
  - due_date
  - confidence
  - source_message_id
  - created_at
- tool_invocations
  - id
  - conversation_id
  - tool_name
  - provider
  - request_payload
  - response_payload
  - status
  - error
  - duration_ms
  - created_at

### Why this schema is enough for MVP

- It supports multi-tenancy without over-designing.
- It keeps conversations platform-agnostic and future-proof.
- It stores enough metadata for debugging and AI review.

## 5. Module responsibilities

### API module

Responsible for transport and validation only.

- parse requests
- validate body/query params
- call services
- return structured responses

### Auth module

Responsible for login, JWT issuance, refresh tokens, and OAuth callback handling.

### Dashboard module

Responsible for organization/workspace management and integration status views.

### AI module

Responsible for:

- conversation understanding
- planning
- deciding which tool to call
- formatting the final response

It should never directly touch the database or secrets.

### Dispatcher module

Responsible for:

- selecting the right provider
- passing validated arguments
- handling retries and logging
- returning normalized results

### Provider module

Responsible for provider-specific API implementation only.

- GitHubProvider creates issues
- JiraProvider creates tickets
- NotionProvider creates pages

### Credentials module

Responsible for encrypting and decrypting stored tokens using a symmetric key.

## 6. Authentication flow

1. User visits the dashboard and chooses a login method.
2. Backend redirects to the appropriate OAuth provider.
3. Provider returns an authorization code.
4. Backend exchanges the code for access and refresh tokens.
5. Backend stores encrypted tokens and creates a session.
6. Backend issues JWT access and refresh tokens.
7. Frontend uses the JWT for all authenticated API calls.

## 7. OAuth flow

Use a shared registry pattern:

```text
OAuth Registry
  ↓
GitHubOAuth / SlackOAuth / GoogleOAuth / NotionOAuth / MicrosoftOAuth / DiscordOAuth
```

Each provider implements the same interface:

- get_authorization_url()
- exchange_code()
- refresh_token()
- revoke_token()

This keeps authentication generic and makes future providers trivial to add.

## 8. Conversation flow

```text
Conversation
  ↓
Conversation Loader
  ↓
Conversation Summarizer
  ↓
Decision Extractor
  ↓
Action Extractor
  ↓
Planner
  ↓
Execution
  ↓
Reply Generator
```

### Flow details

1. Incoming Slack or Teams event is received.
2. Backend normalizes the event into a common conversation shape.
3. The loader stores the message thread and metadata.
4. The summarizer produces a short context summary.
5. The extractor identifies bugs, decisions, blockers, owners, priorities, deadlines.
6. The planner decides whether to create an issue, ticket, or page.
7. The dispatcher executes the provider action.
8. The reply generator sends a confirmation back to the user.

## 9. LangGraph flow

LangGraph is used only for reasoning and planning.

### Suggested nodes

- ingest_message
- summarize_context
- extract_intents
- plan_action
- validate_plan
- execute_tool
- format_reply

### LangGraph responsibilities

- understand the conversation
- decide the next action
- shape tool arguments
- format the final response

It should never directly handle secrets or call external APIs.

## 10. Tool execution flow

```text
LangGraph
  ↓
Execution Engine
  ↓
Dispatcher
  ↓
Credential Manager
  ↓
Provider
  ↓
External API
```

### Execution engine responsibilities

- validate arguments
- log the attempt
- capture timing and errors
- support retries later
- support approval and audit later

## 11. Dashboard flow

1. User signs in.
2. User selects or creates an organization.
3. User invites teammates.
4. User connects GitHub, Jira, or Notion.
5. Dashboard shows connected accounts and integration statuses.
6. Activity view shows recent conversations and executed actions.

## 12. API endpoints

### Auth

- POST /api/auth/login
- POST /api/auth/refresh
- GET /api/auth/google/login
- GET /api/auth/slack/login
- GET /api/auth/github/login
- GET /api/auth/notion/login
- GET /api/auth/:provider/callback

### Dashboard

- GET /api/dashboard/workspaces
- GET /api/dashboard/workspaces/{id}/integrations
- POST /api/dashboard/workspaces
- DELETE /api/dashboard/workspaces/{id}/integrations/{integration_id}

### Integrations

- GET /api/integrations/{provider}/connect
- GET /api/integrations/{provider}/callback

### Webhooks

- POST /api/webhooks/slack
- POST /api/webhooks/teams
- POST /api/webhooks/discord

### Conversations and chat

- POST /api/chat
- GET /api/conversations/{id}
- GET /api/conversations/{id}/messages

## 13. Provider interfaces

Keep provider interfaces intentionally small.

```python
class GitHubProvider:
    async def create_issue(self, repo: str, title: str, body: str) -> dict: ...

class JiraProvider:
    async def create_issue(self, project: str, title: str, description: str) -> dict: ...

class NotionProvider:
    async def create_page(self, title: str, content: str) -> dict: ...
```

The dispatcher knows which provider to invoke; the AI only passes structured arguments.

## 14. Database models

The initial model set should be:

- Organization
- User
- Membership
- Integration
- Credential
- Conversation
- Message
- ActionItem
- ToolInvocation
- Session

This covers the MVP needs without introducing speculative tables.

## 15. Security considerations

- Encrypt stored credentials with a strong symmetric key.
- Never expose OAuth tokens to the AI layer.
- Use JWT access and refresh tokens.
- Use role-based access control for organization data.
- Validate request bodies and provider arguments.
- Separate secrets from application logic.
- Use HTTPS in production and store secrets in environment variables or a secret manager.

## 16. Deployment plan

Use Docker Compose for MVP.

### Services

- FastAPI backend
- Next.js frontend
- PostgreSQL
- Redis

### Environment variables

- DATABASE_URL
- REDIS_URL
- JWT_SECRET
- REFRESH_SECRET
- ATLAS_MASTER_KEY
- GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET
- SLACK_CLIENT_ID / SLACK_CLIENT_SECRET
- GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
- NOTION_CLIENT_ID / NOTION_CLIENT_SECRET

## 17. MVP implementation sequence

1. Auth and organization onboarding
2. OAuth integration storage and dashboard connectivity
3. Slack webhook ingestion and conversation persistence
4. Conversation summarization and structured extraction
5. GitHub issue creation flow
6. Jira and Notion provider integration
7. Activity dashboard and action visibility

## 18. Product framing

Atlas should be positioned as:

> Atlas understands conversations. Everything else is an execution plugin.

That framing keeps the product focused and prevents the MVP from drifting into a generic chatbot or automation platform.
