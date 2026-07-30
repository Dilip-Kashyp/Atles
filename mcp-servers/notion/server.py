from mcp.server.fastmcp import FastMCP
from tools import search_notion_docs

# Initialize FastMCP server
mcp = FastMCP("Notion MCP Server")

@mcp.tool()
async def find_document(query: str) -> str:
    """Searches the Notion workspace for documentation matching the query."""
    return await search_notion_docs(query)

if __name__ == "__main__":
    mcp.run()
