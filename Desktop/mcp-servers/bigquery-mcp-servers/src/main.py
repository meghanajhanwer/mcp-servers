# src/main.py
from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from mcp.server.sse import SseServerTransport

from .settings import Settings
from .services.bigquery_client import BigQueryService
from .services.secrets import AuthError, TokenStore
from .mcp.server import build_mcp_server


# Load .env in local dev (safe in prod too; if no .env, it's a no-op)
load_dotenv()

settings = Settings()

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("bigquery-mcp")

# Create shared services
token_store = TokenStore.from_settings(settings)
bq_service = BigQueryService.from_settings(settings)

# Build MCP server (tools registration)
mcp = build_mcp_server(settings=settings, bq_service=bq_service)

# SSE transport (client will POST messages to /messages/?session_id=...)
transport = SseServerTransport("/messages/")


def create_app() -> FastAPI:
    
    docs_url = "/docs" if settings.docs_enabled() else None
    openapi_url = "/openapi.json" if settings.docs_enabled() else None

    app = FastAPI(
        title="BigQuery MCP Server",
        version="0.1.0",
        docs_url=docs_url,
        openapi_url=openapi_url,
    )
    app.state.settings = settings

    # -------------------------
    # Middleware: Bearer auth
    # -------------------------
    @app.middleware("http")
    async def bearer_auth(request: Request, call_next):
        path = request.url.path

        # Allow health and (optionally) docs without auth
        if path in {"/", "/healthz"}:
            return await call_next(request)
        if settings.docs_enabled() and path in {"/docs", "/openapi.json"}:
            return await call_next(request)

        try:
            token_label = token_store.authenticate_request(request)
            request.state.token_label = token_label
        except AuthError as e:
            return JSONResponse({"error": "unauthorized", "detail": str(e)}, status_code=401)

        return await call_next(request)

    # -------------------------
    # Health / basic endpoint
    # -------------------------
    @app.get("/")
    async def root():
        return {"service": "bigquery-mcp", "status": "ok"}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    # -------------------------
    # MCP SSE endpoint
    # -------------------------
    @app.get("/sse")
    async def sse_endpoint(request: Request):
        """
        Establishes the SSE stream and then runs the MCP protocol over it.

        Important: must return a Response() after the SSE session ends,
        otherwise Starlette may throw a NoneType callable error on disconnect.
        """
        # If auth is enabled, middleware has already validated the request here.
        async with transport.connect_sse(request.scope, request.receive, request._send) as (in_stream, out_stream):
            # NOTE: `_mcp_server` is internal in the SDK but is the common pattern for SSE integration.
            await mcp._mcp_server.run(
                in_stream,
                out_stream,
                mcp._mcp_server.create_initialization_options(),
            )
        return Response()

    # Client POSTs MCP messages to /messages/?session_id=...
    app.mount("/messages", transport.handle_post_message)

    return app


app = create_app()