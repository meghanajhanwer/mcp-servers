# src/mcp/server.py
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..settings import Settings
from ..services.github_client import GitHubService
from .tools.github import register_github_tools


def build_mcp_server(*, settings: Settings, github_service: GitHubService) -> FastMCP:
    """
    Create FastMCP instance and register GitHub tools.
    """
    mcp = FastMCP("github-mcp", json_response=True)
    register_github_tools(mcp=mcp, settings=settings, github_service=github_service)
    return mcp