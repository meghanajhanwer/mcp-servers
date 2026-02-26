from fastapi import FastAPI, Request
from .settings import Settings
from .services.secrets import TokenStore

settings = Settings()
app = FastAPI()

# Only load TokenStore if NOT using Cloud Run IAM
token_store = None
if settings.auth_mode.lower() != "iam":
    token_store = TokenStore.from_settings(settings)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # In Cloud Run IAM mode, Cloud Run already authenticates callers.
    if settings.auth_mode.lower() == "iam":
        return await call_next(request)

    # Optional: allow healthz without auth
    if request.url.path in ("/healthz", "/"):
        return await call_next(request)

    # Bearer token auth for local/dev mode
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return JSONResponse({"error": "unauthorized", "detail": "Missing Bearer token"}, status_code=401)

    token = auth.split(" ", 1)[1].strip()
    if not token_store or not token_store.is_valid(token):
        return JSONResponse({"error": "unauthorized", "detail": "Invalid token"}, status_code=401)

    return await call_next(request)