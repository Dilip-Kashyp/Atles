# Atlas Architecture & System Design

Atlas is a modular enterprise AI platform designed to transform team conversations into structured, executable work.

---

## 1. Core Architecture Principles

1. **Modular Monolith**: Clean separation between Identity, Workspace, Integrations, AI Orchestration, and Ingress layers without microservice network overhead.
2. **Multi-Tenant Provider Resolution**: Webhook events resolve tenant credentials dynamically from encrypted database storage rather than static environment variables.
3. **Decoupled AI Orchestration**: The Gemini-based LLM engine relies on a standardized tool dispatcher and normalized platform events.
4. **Secure Token Lifecycle**: Access tokens (JWT) paired with server-side opaque refresh token rotation via HTTP-only cookies.

---

## 2. System Architecture Overview

```text
       Slack Events / Web Dashboard / API Requests
                           │
                           ▼
                    FastAPI API (v1)
                           │
   ┌───────────────────────┼───────────────────────┐
   ▼                       ▼                       ▼
Identity / Auth      Integrations         Multi-Tenant Ingress
(Session & Cookie)  (Encrypted Creds)    (Slack Team ID -> Token)
   │                       │                       │
   └───────────────────────┼───────────────────────┘
                           │
                           ▼
                 Gemini Orchestrator
                           │
                           ▼
                 Tool Dispatcher & Execution
```

---

## 3. Database Schema & Multi-Tenancy Models

Managed via SQLAlchemy async models and Alembic migrations.

### Key Tables:
- **`users`**: User identity records (`id`, `email`, `full_name`, `is_active`).
- **`organizations`** & **`workspaces`**: Tenancy hierarchy.
- **`sessions`**: Active user sessions (`session_key`, `ip_address`, `expires_at`).
- **`refresh_tokens`**: Opaque SHA-256 hashed refresh tokens (`token_hash`, `used_at`, `replaced_by_id`).
- **`integrations`**: Bound provider connections (`provider_type`, `provider_variant`, `provider_workspace_id`, `status`).
- **`credentials`**: Symmetric-encrypted provider access/refresh tokens (`encrypted_token`, `encrypted_refresh`).

---

## 4. Multi-Tenant Webhook Resolution Flow

1. **Slack Webhook**: Receives `POST /slack/events` payload containing `team_id`.
2. **Signature & Dedup**: `SlackWebhookHandler` verifies `X-Slack-Signature` and checks in-memory event deduplication queue.
3. **Tenant Lookup**: Queries `integrations` table where `provider_type = 'slack'` and `provider_workspace_id = team_id`.
4. **Token Decryption**: `CredentialManager` decrypts the Fernet-encrypted bot token.
5. **Dynamic Platform Instance**: Creates a request-scoped `SlackPlatform(WebClient(token))` and dispatches execution to `Orchestrator` in a background task.

---

## 5. Security & Authentication Design

- **Access Tokens**: Short-lived JWTs (15 min) containing `sub` (user_id) and `sid` (session_id).
- **Refresh Tokens**: Long-lived opaque strings (30 days) stored as SHA-256 hashes in DB.
- **Cookie Security**: `refresh_token` set via `set_cookie(httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")`.
- **Token Reuse Detection**: If a previously used refresh token is presented, all user sessions are immediately revoked to prevent theft.
