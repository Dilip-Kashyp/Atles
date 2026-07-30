FROM python:3.11-slim

WORKDIR /mcp

RUN pip install mcp notion-client

COPY . .

CMD ["python", "server.py"]
