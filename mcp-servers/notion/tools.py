import os
import logging
from notion_client import Client
from notion_client.errors import APIResponseError

log = logging.getLogger(__name__)

async def search_notion_docs(query: str) -> str:
    """
    Searches the Notion workspace for pages matching the query.
    """
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        return "Error: NOTION_TOKEN environment variable is not set on the MCP server."

    try:
        # Note: notion_client is synchronous by default, but wrapping it in an async function 
        # is fine for this lightweight implementation since it's dispatched by FastMCP.
        # Alternatively, AsyncClient can be used if preferred.
        from notion_client import AsyncClient
        notion = AsyncClient(auth=token)
        
        response = await notion.search(query=query, filter={"value": "page", "property": "object"})
        results = response.get("results", [])
        
        if not results:
            return f"No documents found for query: '{query}'"
            
        results_str = f"Found {len(results)} result(s) for '{query}':\n\n"
        for page in results:
            title = "Untitled"
            properties = page.get("properties", {})
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "title":
                    title_arr = prop_data.get("title", [])
                    if title_arr:
                        title = title_arr[0].get("plain_text", "Untitled")
                    break
            
            url = page.get("url", "No URL")
            results_str += f"- Title: {title}\n  URL: {url}\n"
            
        log.info(f"Successfully completed Notion search for: {query}")
        return results_str
    except APIResponseError as e:
        log.error(f"Notion API Error: {e}")
        return f"Error communicating with Notion API: {e}"
    except Exception as e:
        log.exception("Unexpected error in search_notion_docs")
        return f"Unexpected error: {str(e)}"
