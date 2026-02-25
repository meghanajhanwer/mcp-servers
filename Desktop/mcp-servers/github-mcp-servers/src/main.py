# src/main.py
from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from mcp.server.sse import SseServerTransport

from .settings import Settings
from .services.github_client import GitHubService
from .services.secrets import AuthError, TokenStore
from .mcp.server import build_mcp_server

# Load .env in local dev (safe in prod too; if no .env, it's a no-op)
load_dotenv()

settings = Settings()

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("github-mcp")

# Shared services
token_store = TokenStore.from_settings(settings)
github_service = GitHubService.from_settings(settings)

# MCP server wiring
mcp = build_mcp_server(settings=settings, github_service=github_service)

# SSE transport (client will POST messages to /messages/?session_id=...)
transport = SseServerTransport("/messages/")


def create_app() -> FastAPI:
    docs_url = "/docs" if settings.docs_enabled() else None
    openapi_url = "/openapi.json" if settings.docs_enabled() else None

    app = FastAPI(
        title="GitHub MCP Server",
        version="0.1.0",
        docs_url=docs_url,
        openapi_url=openapi_url,
    )

    # -------------------------
    # Middleware: Bearer auth
    # -------------------------
    @app.middleware("http")
    async def bearer_auth(request: Request, call_next):
        path = request.url.path

        # Allow health & root without auth (optional).
        # If you want max security, remove "/" and "/healthz" from this allowlist.
        if path in {"/", "/healthz"}:
            return await call_next(request)

        # Allow docs in dev
        if settings.docs_enabled() and path in {"/docs", "/openapi.json"}:
            return await call_next(request)

        try:
            label = token_store.authenticate_request(request)
            request.state.token_label = label
        except AuthError as e:
            return JSONResponse({"error": "unauthorized", "detail": str(e)}, status_code=401)

        return await call_next(request)

    # -------------------------
    # Health / root
    # -------------------------
    @app.get("/")
    async def root():
        return {"service": "github-mcp", "status": "ok"}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    # -------------------------
    # MCP SSE endpoint
    # -------------------------
    @app.get("/sse")
    async def sse_endpoint(request: Request):
        """
        Establish SSE stream and run MCP over it.
        """
        async with transport.connect_sse(request.scope, request.receive, request._send) as (in_stream, out_stream):
            await mcp._mcp_server.run(
                in_stream,
                out_stream,
                mcp._mcp_server.create_initialization_options(),
            )
        return Response()

    # Client POSTs MCP messages to /messages/?session_id=...
    app.mount("/messages", transport.handle_post_message)

    @app.on_event("shutdown")
    def shutdown():
        github_service.close()

    return app


app = create_app()