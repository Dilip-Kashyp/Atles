# Deployment Guide

This project can be deployed using Docker Compose for self-hosting or Vercel/Serverless for the backend.

## Docker Deployment (Recommended)
Each component (Backend, Slack MCP, GitHub MCP, etc.) has its own Dockerfile. The `docker-compose.yml` links them together.

1. Create a `.env` file from `.env.example`.
2. Run `docker-compose up -d --build`.
3. Use a reverse proxy (e.g., Nginx, Caddy, or Cloudflare Tunnels) to expose port 8000 for Slack webhooks.

## Vercel / Serverless Deployment
The `backend/` directory can be deployed as a serverless function on Vercel. 
- You must adapt the MCP client to use SSE (Server-Sent Events) over HTTP rather than `stdio` subprocesses if deploying in a serverless environment, since subprocess execution is often restricted.
- The `vercel.json` provides the build configuration.
