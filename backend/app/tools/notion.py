import json
import logging
from typing import Any

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

from app.tools.base import BaseTool

log = logging.getLogger(__name__)


class NotionSearchTool(BaseTool):
    """Searches the Notion workspace for pages matching a query."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return "find_document"

    @property
    def description(self) -> str:
        return "Searches the Notion workspace for documentation or pages matching the query."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term to look up in Notion",
                },
            },
            "required": ["query"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        query = arguments["query"]
        log.info("[CHECKPOINT: NOTION_SEARCH_START] Searching Notion for: '%s'", query)

        try:
            notion = AsyncClient(auth=self._token)
            response = await notion.search(
                query=query,
                filter={"value": "page", "property": "object"},
            )
            results = response.get("results", [])

            if not results:
                log.info("[CHECKPOINT: NOTION_SEARCH_EMPTY] No results for '%s'", query)
                return json.dumps({"results": [], "info": f"No documents found for '{query}'"})

            pages = []
            for page in results:
                title = _extract_page_title(page)
                pages.append({
                    "title": title,
                    "url":   page.get("url", ""),
                    "id":    page.get("id", ""),
                })

            log.info("[CHECKPOINT: NOTION_SEARCH_DONE] Found %d result(s)", len(pages))
            return json.dumps({"query": query, "count": len(pages), "results": pages})

        except APIResponseError as exc:
            log.error("[CHECKPOINT: NOTION_SEARCH_ERROR] API error: %s", exc)
            return json.dumps({"error": f"Notion API error: {exc}"})
        except Exception as exc:
            log.exception("[CHECKPOINT: NOTION_SEARCH_ERROR] Unexpected error")
            return json.dumps({"error": f"Unexpected error: {exc}"})


def _extract_page_title(page: dict) -> str:
    for prop_data in page.get("properties", {}).values():
        if prop_data.get("type") == "title":
            arr = prop_data.get("title", [])
            if arr:
                return arr[0].get("plain_text", "Untitled")
    return "Untitled"
