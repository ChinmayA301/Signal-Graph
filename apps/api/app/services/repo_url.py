from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedRepo:
    owner: str
    name: str


_GITHUB_REPO_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+)/?$",
    re.IGNORECASE,
)


def parse_github_repo_url(repo_url: str) -> ParsedRepo:
    text = repo_url.strip()
    match = _GITHUB_REPO_PATTERN.match(text)
    if not match:
        raise ValueError("Expected a URL like https://github.com/owner/name")
    owner = match.group("owner")
    name = match.group("name").removesuffix(".git")
    return ParsedRepo(owner=owner, name=name)
