# src/services/github_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from ..settings import Settings


@dataclass(frozen=True)
class GitHubOwner:
    login: str
    owner_type: str  # "User" or "Organization"


class GitHubService:
    """
    Minimal GitHub REST API wrapper (read-only).
    Uses PAT / token if provided to avoid tight unauth rate limits.
    """

    def __init__(self, *, base_url: str, token: str | None, user_agent: str, timeout_seconds: int) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            # Works for fine-grained PATs and GitHub App user tokens
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_seconds)

    @classmethod
    def from_settings(cls, settings: Settings) -> "GitHubService":
        token = settings.github_token_secret_payload or settings.github_token
        return cls(
            base_url=settings.github_api_base_url,
            token=token,
            user_agent=settings.github_user_agent,
            timeout_seconds=settings.github_timeout_seconds,
        )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    # -------------------------
    # Core helpers
    # -------------------------
    def _get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def resolve_owner(self, owner: str) -> GitHubOwner:
        data = self._get_json(f"/users/{owner}")
        otype = data.get("type")  # "User" or "Organization"
        if not otype:
            otype = "User"
        return GitHubOwner(login=data.get("login", owner), owner_type=otype)

    # -------------------------
    # Public methods
    # -------------------------
    def list_repos(self, owner: str) -> List[Dict[str, Any]]:
        """
        Lists repos for user or org (auto-detected).
        Returns lightweight metadata.
        """
        resolved = self.resolve_owner(owner)
        path = f"/orgs/{resolved.login}/repos" if resolved.owner_type == "Organization" else f"/users/{resolved.login}/repos"

        repos: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        # Fetch a single page by default; can expand later if needed.
        data = self._get_json(path, params={"per_page": per_page, "page": page, "sort": "pushed", "direction": "desc"})

        for r in data:
            repos.append(
                {
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "private": r.get("private"),
                    "default_branch": r.get("default_branch"),
                    "pushed_at": r.get("pushed_at"),
                    "updated_at": r.get("updated_at"),
                    "html_url": r.get("html_url"),
                }
            )
        return repos

    def _get_default_branch(self, owner: str, repo: str) -> str:
        data = self._get_json(f"/repos/{owner}/{repo}")
        branch = data.get("default_branch") or "main"
        return branch

    def latest_commit(self, owner: str, repo: str, branch: Optional[str]) -> Dict[str, Any]:
        """
        Latest commit on branch (default branch if None).
        """
        br = branch or self._get_default_branch(owner, repo)
        data = self._get_json(f"/repos/{owner}/{repo}/commits/{br}")

        commit = data.get("commit", {}) or {}
        author = (data.get("author") or {}).get("login")
        committer = (data.get("committer") or {}).get("login")

        msg = (commit.get("message") or "").splitlines()[0][:240]
        date = None
        # Prefer committer date; fallback to author date
        if commit.get("committer") and commit["committer"].get("date"):
            date = commit["committer"]["date"]
        elif commit.get("author") and commit["author"].get("date"):
            date = commit["author"]["date"]

        return {
            "branch": br,
            "sha": data.get("sha"),
            "message": msg,
            "date": date,
            "author": author,
            "committer": committer,
            "html_url": data.get("html_url"),
        }

    def latest_commits(self, owner: str, repo: str, limit: int, branch: Optional[str]) -> List[Dict[str, Any]]:
        """
        Latest N commits on branch (default branch if None).
        """
        br = branch or self._get_default_branch(owner, repo)
        data = self._get_json(
            f"/repos/{owner}/{repo}/commits",
            params={"sha": br, "per_page": min(limit, 100), "page": 1},
        )

        out: list[dict[str, Any]] = []
        for item in data[:limit]:
            commit = item.get("commit", {}) or {}
            msg = (commit.get("message") or "").splitlines()[0][:240]

            date = None
            if commit.get("committer") and commit["committer"].get("date"):
                date = commit["committer"]["date"]
            elif commit.get("author") and commit["author"].get("date"):
                date = commit["author"]["date"]

            out.append(
                {
                    "sha": item.get("sha"),
                    "message": msg,
                    "date": date,
                    "html_url": item.get("html_url"),
                    "author": (item.get("author") or {}).get("login"),
                    "committer": (item.get("committer") or {}).get("login"),
                }
            )
        return out

    def latest_commit_across_repos(self, owner: str, max_repos: int) -> Dict[str, Any]:
        """
        Scan up to max_repos repos for owner, and return most recent commit found.
        """
        repos = self.list_repos(owner)
        repos_to_scan = repos[:max_repos]

        best: dict[str, Any] | None = None

        for r in repos_to_scan:
            full_name = r.get("full_name")
            if not full_name or "/" not in full_name:
                continue
            o, repo = full_name.split("/", 1)

            try:
                commit = self.latest_commit(o, repo, r.get("default_branch"))
            except httpx.HTTPStatusError:
                # Skip repos we can't access
                continue

            # Compare ISO timestamps as strings (safe for same format: YYYY-MM-DDTHH:MM:SSZ)
            if not best or (commit.get("date") and commit["date"] > (best.get("date") or "")):
                best = {
                    "repo": full_name,
                    **commit,
                }

        return {
            "scanned_repos": len(repos_to_scan),
            "latest": best or {"error": "No commits found (or no accessible repos)."},
        }