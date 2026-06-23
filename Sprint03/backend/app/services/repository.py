import re
from urllib.parse import urlparse

MARKDOWN_LINK_RE = re.compile(r"^\[[^\]]+\]\((?P<url>[^)]+)\)$")


class RepositoryUrlError(ValueError):
    pass


def normalize_repository_url(repository_url: str) -> str:
    candidate = repository_url.strip()
    match = MARKDOWN_LINK_RE.match(candidate)
    if match:
        candidate = match.group("url").strip()

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https", "ssh", "git"} and not candidate.startswith("git@"):
        raise RepositoryUrlError("Repository URL must be an HTTP(S), SSH, or Git URL.")
    return candidate
