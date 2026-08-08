# Deployment & Infrastructure Guide

This guide outlines deployment options for hosting Atlas in local development, staging, and production environments.

---

## 1. Docker Compose Setup (Production / Self-Hosting)

The project includes a root `docker-compose.yml` configured with:
- **`backend`**: FastAPI application container.
- **`frontend`**: Next.js 15 dashboard container.
- **`atlas_db`**: PostgreSQL 16 database.
- **`atlas_redis`**: Redis 7.4 cache store.

### Commands:

```bash
# Build and launch all services in detached mode
docker compose up -d --build

# Run database migrations
docker compose exec backend alembic upgrade head

# View backend logs
docker compose logs backend -f
```

---

## 2. Exposing Webhooks (Development)

Because Provider APIs (Slack, GitHub) require a public HTTPS endpoint to deliver webhooks, use a public tunnel during local development:

```bash
# Expose port 8000 using localtunnel
npx localtunnel --port 8000
```

### Slack Setup
Set the public URL in your Slack App settings under **Event Subscriptions**:
`https://<your-subdomain>.loca.lt/slack/events`

### GitHub Setup
Set the public URL in your GitHub App settings under **General -> Webhook**:
`https://<your-subdomain>.loca.lt/api/v1/webhooks/github`

---

## 3. Production Deployment Notes

- **Reverse Proxy**: Place an Nginx, Caddy, or Cloudflare Tunnel in front of the backend container (`port 8000`) and frontend container (`port 3000`).
- **HTTPS & Secure Cookies**: Set `COOKIE_SECURE=true` in `.env` when serving over HTTPS so `refresh_token` cookies enforce transport security.
- **Master Encryption Key**: Generate a secure 32-byte key for `ATLAS_MASTER_KEY` to encrypt stored integration tokens.
