import os
import logging
from github import Github
from github.GithubException import GithubException

log = logging.getLogger(__name__)

async def create_github_issue(repo: str, title: str, body: str) -> str:
    """
    Creates a GitHub issue in the specified repository.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return "Error: GITHUB_TOKEN environment variable is not set on the MCP server."

    try:
        g = Github(token)
        repository = g.get_repo(repo)
        issue = repository.create_issue(title=title, body=body)
        log.info(f"Successfully created GitHub issue: {issue.html_url}")
        return f"Successfully created issue '{title}'. Issue URL: {issue.html_url}"
    except GithubException as e:
        error_msg = e.data.get('message', str(e)) if hasattr(e, 'data') and isinstance(e.data, dict) else str(e)
        log.error(f"GitHub API Error: {error_msg}")
        return f"Error creating GitHub issue: {error_msg}"
    except Exception as e:
        log.exception("Unexpected error in create_github_issue")
        return f"Unexpected error: {str(e)}"
