FROM python:3.11-slim

WORKDIR /mcp

# Setup slack MCP server dependencies
RUN pip install mcp slack-sdk

COPY . .

CMD ["python", "server.py"]
