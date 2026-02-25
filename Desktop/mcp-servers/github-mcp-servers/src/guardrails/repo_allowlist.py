# src/guardrails/repo_allowlist.py
from __future__ import annotations

import fnmatch


def parse_allowlist(value: str | None) -> list[str]:
    """
    Parse comma-separated allowlist patterns.
    Patterns support wildcards using fnmatch, e.g.:
      - "myorg/*"
      - "myorg/repo1"
      - "myuser/*"
    Empty/None => allow all.
    """
    if not value:
        return []
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p]


def is_allowed(owner: str, repo: str, patterns: list[str]) -> bool:
    """
    Return True if owner/repo matches any allowlist pattern.
    If patterns is empty => allow all.
    """
    if not patterns:
        return True
    target = f"{owner}/{repo}"
    return any(fnmatch.fnmatchcase(target, pat) for pat in patterns)


def require_allowed(owner: str, repo: str, patterns: list[str]) -> None:
    if not is_allowed(owner, repo, patterns):
        raise ValueError(
            f"Repository '{owner}/{repo}' is not allowed by server policy. "
            f"Ask an admin to add it to GITHUB_ALLOWED_REPOS."
        )