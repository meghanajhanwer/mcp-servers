# src/mcp/server.py
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..settings import Settings
from ..services.graph_client import GraphCalendarService
from .tools.outlook import register_outlook_tools


def build_mcp_server(*, settings: Settings, graph_service: GraphCalendarService) -> FastMCP:
    mcp = FastMCP("outlook-mcp", json_response=True)
    register_outlook_tools(mcp=mcp, settings=settings, graph_service=graph_service)
    return mcp