import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from app.config.settings import settings

MARKDOWN_LINK_RE = re.compile(r"^\[[^\]]+\]\((?P<url>[^)]+)\)$")


class RepositoryCloneError(RuntimeError):
    pass


def normalize_repository_url(repository_url: str) -> str:
    candidate = repository_url.strip()
    match = MARKDOWN_LINK_RE.match(candidate)
    if match:
        candidate = match.group("url").strip()

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https", "ssh", "git"} and not candidate.startswith("git@"):
        raise RepositoryCloneError("Repository URL must be an HTTP(S), SSH, or Git URL.")
    return candidate


def clone_repository(repository_url: str, scan_id: str) -> Path:
    normalized_url = normalize_repository_url(repository_url)
    workspace_root = Path(settings.scan_workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)
    scan_workspace = workspace_root / scan_id
    if scan_workspace.exists():
        shutil.rmtree(scan_workspace)
    scan_workspace.mkdir(parents=True)

    repo_path = scan_workspace / "repository"
    command = ["git", "clone", "--depth", "1", normalized_url, str(repo_path)]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=settings.scan_timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        raise RepositoryCloneError(result.stderr.strip() or result.stdout.strip() or "Repository clone failed.")
    return repo_path
