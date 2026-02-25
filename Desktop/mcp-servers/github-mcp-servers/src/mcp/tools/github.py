# src/mcp/tools/github.py
from __future__ import annotations

import anyio
from mcp.server.fastmcp import FastMCP

from ...guardrails.limits import clamp_int
from ...services.github_client import GitHubService
from ...settings import Settings
from ...guardrails.repo_allowlist import parse_allowlist, require_allowed


def register_github_tools(*, mcp: FastMCP, settings: Settings, github_service: GitHubService) -> None:
    @mcp.tool()
    async def github_list_repos(owner: str) -> dict:
        """
        List repos for a GitHub user or org (auto-detected).
        Returns lightweight repo metadata.
        """
        owner = owner.strip()
        if not owner:
            raise ValueError("owner is required")

        repos = await anyio.to_thread.run_sync(
            github_service.list_repos,
            owner,
            cancellable=True,
        )
        return {"ok": True, "owner": owner, "repo_count": len(repos), "repos": repos}

    @mcp.tool()
    async def github_latest_commit(owner: str, repo: str, branch: str | None = None) -> dict:
        """
        Get latest commit for a repo (default branch if branch not provided).
        """
        owner = owner.strip()
        repo = repo.strip()
        if not owner or not repo:
            raise ValueError("owner and repo are required")

        commit = await anyio.to_thread.run_sync(
            github_service.latest_commit,
            owner,
            repo,
            branch,
            cancellable=True,
        )
        return {"ok": True, "owner": owner, "repo": repo, "branch": commit.get("branch"), "commit": commit}

    @mcp.tool()
    async def github_latest_commits(owner: str, repo: str, limit: int = 5, branch: str | None = None) -> dict:
        """
        Get latest commits for a repo (default branch if branch not provided).
        """
        owner = owner.strip()
        repo = repo.strip()
        if not owner or not repo:
            raise ValueError("owner and repo are required")

        limit = clamp_int(limit, default=5, min_value=1, max_value=settings.github_max_commits_return)

        commits = await anyio.to_thread.run_sync(
            github_service.latest_commits,
            owner,
            repo,
            limit,
            branch,
            cancellable=True,
        )
        return {"ok": True, "owner": owner, "repo": repo, "limit": limit, "commits": commits}

    @mcp.tool()
    async def github_latest_commit(owner: str, repo: str, branch: str | None = None) -> dict:
        owner = owner.strip()
        repo = repo.strip()
        if not owner or not repo:
            raise ValueError("owner and repo are required")

        patterns = parse_allowlist(settings.github_allowed_repos)
        require_allowed(owner, repo, patterns)

        commit = await anyio.to_thread.run_sync(
            github_service.latest_commit,
            owner,
            repo,
            branch,
            cancellable=True,
        )
        return {"ok": True, "owner": owner, "repo": repo, "branch": commit.get("branch"), "commit": commit}