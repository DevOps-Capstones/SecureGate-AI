import re
from urllib.parse import urlparse, urlunparse

MARKDOWN_LINK_RE = re.compile(r"^\[[^\]]+\]\((?P<url>[^)]+)\)$")


class RepositoryUrlError(ValueError):
    pass


def normalize_repository_url(repository_url: str) -> str:
    candidate = repository_url.strip()
    match = MARKDOWN_LINK_RE.match(candidate)
    if match:
        candidate = match.group("url").strip()

    if candidate.startswith("git@"):
        try:
            host, path = candidate.split(":", 1)
            owner_repo = path.removesuffix(".git").strip("/")
            return f"https://{host.replace('git@', '').lower()}/{owner_repo.lower()}"
        except ValueError:
            raise RepositoryUrlError("Repository URL must be a valid Git SSH URL.") from None

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https", "ssh", "git"}:
        raise RepositoryUrlError("Repository URL must be an HTTP(S), SSH, or Git URL.")
    if not parsed.netloc or not parsed.path.strip("/"):
        raise RepositoryUrlError("Repository URL must include a host and repository path.")
    path = parsed.path.removesuffix(".git").rstrip("/")
    normalized = urlunparse(("https", parsed.netloc.lower(), path.lower(), "", "", ""))
    return normalized


def safe_repository_url(repository_url: str | None) -> str:
    if not repository_url:
        return "Not available"
    candidate = str(repository_url).strip()
    match = MARKDOWN_LINK_RE.match(candidate)
    if match:
        candidate = match.group("url").strip()
    try:
        return normalize_repository_url(candidate)
    except RepositoryUrlError:
        return candidate
