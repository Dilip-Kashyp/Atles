import asyncio
import json
import logging
from typing import Any

from github import Github
from github.GithubException import GithubException

from app.tools.base import BaseTool

log = logging.getLogger(__name__)


class GithubIssueTool(BaseTool):
    """Creates a new GitHub issue via the GitHub REST API (PyGithub)."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return "open_issue"

    @property
    def description(self) -> str:
        return (
            "Creates a new issue in the specified GitHub repository. "
            "Repo must be in 'owner/repo' format."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo":  {"type": "string", "description": "Repository in 'owner/repo' format"},
                "title": {"type": "string", "description": "Issue title"},
                "body":  {"type": "string", "description": "Issue body / description"},
            },
            "required": ["repo", "title", "body"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        repo  = arguments["repo"]
        title = arguments["title"]
        body  = arguments["body"]

        log.info("[CHECKPOINT: GITHUB_ISSUE_START] Creating issue in '%s': %s", repo, title)

        try:
            result = await asyncio.to_thread(self._create_issue, repo, title, body)
            log.info("[CHECKPOINT: GITHUB_ISSUE_DONE] %s", result)
            return result
        except GithubException as exc:
            msg = (
                exc.data.get("message", str(exc))
                if isinstance(getattr(exc, "data", None), dict)
                else str(exc)
            )
            log.error("[CHECKPOINT: GITHUB_ISSUE_ERROR] GithubException: %s", msg)
            return json.dumps({"error": f"GitHub API error: {msg}"})
        except Exception as exc:
            log.exception("[CHECKPOINT: GITHUB_ISSUE_ERROR] Unexpected error")
            return json.dumps({"error": f"Unexpected error: {exc}"})

    def _create_issue(self, repo: str, title: str, body: str) -> str:
        g = Github(self._token)
        repository = g.get_repo(repo)
        issue = repository.create_issue(title=title, body=body)
        return json.dumps({
            "number": issue.number,
            "title":  issue.title,
            "url":    issue.html_url,
            "state":  issue.state,
        })
