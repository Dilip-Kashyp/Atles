# Atlas — Conversation Intelligence Platform

Atlas is a modular AI platform for turning conversations into structured work. The current implementation is a working MVP that combines a FastAPI backend, a Next.js dashboard, Slack ingress, OAuth login, and a lightweight AI planning layer for turning requests into actions.

---

## What the system does today

Atlas currently supports:
- a web dashboard for connecting integrations
- OAuth sign-in with GitHub, Google, and Slack
- Slack event ingestion and webhook handling
- a backend orchestrator that can process chat and tool-driven requests
- a simple AI pipeline that extracts intent and prepares action plans
- provider-style execution scaffolding for GitHub issue creation

The platform is intentionally built as a modular monolith so it can grow from MVP to a larger multi-tenant product without a full rewrite.

---

## Current architecture

### High-level flow

```text
User / Slack / Web dashboard
        │
        ▼
   API Layer (FastAPI)
        │
        ▼
Conversation + Auth + Integration Services
        │
        ▼
   AI Planning / Workflow Layer
        │
        ▼
   Provider / Tool Execution Layer
        │
        ▼
GitHub / Slack / future Jira / Notion / Google
```

### Core modules

- Backend API routes:
  - auth for OAuth and JWT-style session handoff
  - chat for direct conversational requests
  - slack for event ingestion
  - integrations for provider connection flows
  - dashboard for workspace and integration views

- Backend orchestration:
  - orchestrator/agent.py handles the turn lifecycle
  - workflow/ contains lightweight planning and state execution primitives
  - ai/ contains the current conversation-planning pipeline

- Frontend:
  - Next.js app with a dashboard-style integration center
  - login experience with multiple provider buttons

- Data and auth:
  - SQLAlchemy models for users, workspaces, memberships, and integrations
  - encrypted credential handling for connected providers
  - Redis-backed state handling for OAuth and short-lived flow data

---

## Working implementation status

### Working now
- FastAPI app boots and serves API routes
- Slack webhook and chat endpoints are wired
- OAuth login flow is available for GitHub, Google, and Slack
- Frontend login and dashboard shell render correctly
- AI pipeline can plan a structured action for requests such as issue creation
- Backend tests are passing

### In progress / next milestones
- full provider execution for Jira and Notion
- richer AI reasoning and conversation extraction
- persistent multi-workspace organization model refinement
- real workflow execution tied to provider results
- expanded dashboard analytics and activity views

---

## Backend structure

```text
backend/app/
  api/
    auth.py
    chat.py
    dashboard.py
    integrations.py
    slack.py
    webhooks.py
  auth/
    jwt.py
    oauth_registry.py
  ai/
    graph.py
    planner.py
    extractor.py
    summarizer.py
    formatter.py
    prompts.py
    state.py
  orchestrator/
    agent.py
    platform_base.py
    slack_handler.py
    tool_dispatcher.py
    provider.py
    workflow_bridge.py
  workflow/
    engine.py
    planner.py
    states.py
    tool_registry.py
  credentials/
    manager.py
  models/
    tenancy.py
    integrations.py
  database/
    session.py
  utils/
    redis.py
```

---

## Frontend structure

```text
frontend/src/app/
  layout.tsx
  page.tsx
  globals.css
```

The frontend currently provides the main onboarding and integration experience, while the backend supplies the real API and auth behavior.

---

## Authentication and OAuth flow

The current auth flow is:

1. User selects GitHub, Google, or Slack on the landing screen.
2. Frontend redirects to the backend OAuth route.
3. Backend stores a temporary state value and redirects the user to the OAuth provider.
4. Provider returns an authorization code.
5. Backend exchanges the code, creates or updates the user record, and issues a frontend redirect containing the access token.
6. Frontend stores the token and enters the authenticated dashboard experience.

This flow is implemented through the shared OAuth registry in the backend auth layer.

---

## Current development workflow

### Run the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

### Run tests

```bash
cd backend
python -m pytest -q
```

### Run with Docker

```bash
docker compose up -d --build
```

---

## Environment notes

The application expects the following environment values to be configured:

```env
GEMINI_API_KEY=...
SLACK_BOT_TOKEN=...
SLACK_SIGNING_SECRET=...

GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

If OAuth credentials are not configured, the app still runs in a local/demo-style mode for frontend exploration and backend testing.

---

## Product direction

The current product direction is a practical MVP for Atlas:
- keep the architecture modular
- prioritize reliable integrations over premature complexity
- make the AI pipeline useful for planning and actioning conversations
- expand providers and analytics incrementally

The next major step is to connect the AI planning layer to real provider execution end to end so a user request can flow from conversation to actual GitHub, Jira, or Notion work automatically.

### 1. Environment Setup
```bash
cp .env.example .env
```
Fill in the required secrets:
```env
GEMINI_API_KEY=your_gemini_api_key
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your_signing_secret

# Optional integrations
GITHUB_TOKEN=ghp_your_github_token
NOTION_TOKEN=secret_your_notion_token

# Memory (optional — bot works stateless without it)
MONGODB_URI=mongodb+srv://...
```

### 2. Run Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### 3. Run Tests
```bash
cd backend
python -m pytest ../tests/ -v
# 124 tests · 0 failures
```

### 4. Expose to Slack (Development)
Use [`ngrok`](https://ngrok.com) or similar to expose `localhost:8000`:
```bash
python ng.py
```
Or run directly:
```bash
ngrok http 8000
```
Set your Slack App's Event Subscriptions URL to:
```
https://<your-ngrok-url>/slack/events
```

### 5. Docker (Production)
```bash
docker-compose up -d --build
```
Then point a reverse proxy (Nginx / Caddy / Cloudflare Tunnel) at port `8000`.
