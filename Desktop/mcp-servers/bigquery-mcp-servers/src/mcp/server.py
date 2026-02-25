# src/mcp/server.py
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..settings import Settings
from ..services.bigquery_client import BigQueryService
from .tools.bigquery import register_bigquery_tools


def build_mcp_server(*, settings: Settings, bq_service: BigQueryService) -> FastMCP:
    """
    Creates the FastMCP instance and registers tools.

    json_response=True ensures tool outputs are returned as JSON-friendly payloads.
    """
    mcp = FastMCP("bigquery-mcp", json_response=True)
    register_bigquery_tools(mcp=mcp, settings=settings, bq_service=bq_service)
    return mcp