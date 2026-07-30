from mcp.server.fastmcp import FastMCP
from tools import create_github_issue

# Initialize FastMCP server
mcp = FastMCP("GitHub MCP Server")

@mcp.tool()
async def open_issue(repo: str, title: str, body: str) -> str:
    """Creates a new issue in the specified GitHub repository. Ensure repo is in 'owner/repo' format."""
    return await create_github_issue(repo, title, body)

if __name__ == "__main__":
    mcp.run()
