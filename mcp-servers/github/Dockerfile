FROM python:3.11-slim

WORKDIR /mcp

RUN pip install mcp PyGithub

COPY . .

CMD ["python", "server.py"]
