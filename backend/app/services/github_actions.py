from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, parse, request

from app.config.settings import settings
from app.models.scan import Project


@dataclass
class GitHubDispatchResult:
    status: str
    runner: str
    workflow_file: str
    branch: str
    repository: str
    message: str


def _parse_github_repository(repository_url: str) -> tuple[str, str]:
    parsed = parse.urlparse(repository_url)
    path = parsed.path.strip("/")
    if parsed.netloc.lower() != "github.com" or not path:
        raise ValueError("Only GitHub repository URLs can be triggered from this runner.")
    parts = path.removesuffix(".git").split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError("Repository URL must include GitHub owner and repository name.")
    return parts[0], parts[1]


def trigger_github_actions_scan(project: Project, branch: str = "main") -> GitHubDispatchResult:
    if not settings.github_trigger_token:
        raise ValueError("GITHUB_TRIGGER_TOKEN is not configured in SecureGate AI backend environment.")

    owner, repo = _parse_github_repository(project.repository_url)
    workflow_file = settings.github_workflow_file or "securegate.yml"
    api_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{parse.quote(workflow_file)}/dispatches"
    payload = json.dumps({"ref": branch}).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.github_trigger_token}",
        "Content-Type": "application/json",
        "User-Agent": "SecureGate-AI",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = request.Request(api_url, data=payload, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=20) as response:
            if response.status not in {204, 201, 200}:
                raise ValueError(f"GitHub returned unexpected status {response.status}.")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise ValueError(f"GitHub workflow '{workflow_file}' was not found in {owner}/{repo}, or the token cannot access it.") from exc
        if exc.code in {401, 403}:
            raise ValueError("GitHub token cannot trigger this workflow. Check Actions read/write and repository access permissions.") from exc
        raise ValueError(f"GitHub workflow dispatch failed with status {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise ValueError(f"Could not reach GitHub API: {exc.reason}") from exc

    return GitHubDispatchResult(
        status="TRIGGERED",
        runner="github-actions",
        workflow_file=workflow_file,
        branch=branch,
        repository=f"{owner}/{repo}",
        message="GitHub Actions workflow started successfully.",
    )
