# src/main.py
from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from mcp.server.sse import SseServerTransport

from .settings import Settings
from .services.graph_client import GraphCalendarService
from .services.secrets import AuthError, TokenStore
from .mcp.server import build_mcp_server

load_dotenv()
settings = Settings()

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("outlook-mcp")

token_store = TokenStore.from_settings(settings)
graph_service = GraphCalendarService.from_settings(settings)

mcp = build_mcp_server(settings=settings, graph_service=graph_service)
transport = SseServerTransport("/messages/")


def create_app() -> FastAPI:
    docs_url = "/docs" if settings.docs_enabled() else None
    openapi_url = "/openapi.json" if settings.docs_enabled() else None

    app = FastAPI(
        title="Outlook MCP Server",
        version="0.1.0",
        docs_url=docs_url,
        openapi_url=openapi_url,
    )

    # Bearer auth (MCP server access)
    @app.middleware("http")
    async def bearer_auth(request: Request, call_next):
        path = request.url.path

        # Allow root + health without token (optional).
        # If you want tighter security later, remove this allowlist.
        if path in {"/", "/healthz"}:
            return await call_next(request)

        if settings.docs_enabled() and path in {"/docs", "/openapi.json"}:
            return await call_next(request)

        try:
            label = token_store.authenticate_request(request)
            request.state.token_label = label
        except AuthError as e:
            return JSONResponse({"error": "unauthorized", "detail": str(e)}, status_code=401)

        return await call_next(request)

    @app.get("/")
    async def root():
        return {"service": "outlook-mcp", "status": "ok"}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/sse")
    async def sse_endpoint(request: Request):
        async with transport.connect_sse(request.scope, request.receive, request._send) as (in_stream, out_stream):
            await mcp._mcp_server.run(
                in_stream,
                out_stream,
                mcp._mcp_server.create_initialization_options(),
            )
        return Response()

    app.mount("/messages", transport.handle_post_message)

    @app.on_event("shutdown")
    def shutdown():
        graph_service.close()

    return app


app = create_app()