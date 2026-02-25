# GitHub MCP Server (Custom)

Remote MCP server (SSE) deployed on Cloud Run.

- Auth: `Authorization: Bearer <token>` (server-side)
- GitHub: read-only tools (repos, latest commits)
- CI/CD: Cloud Build -> Artifact Registry -> Cloud Run

## Local run (dev)

1) Create venv and install deps:
   - `python -m venv .venv`
   - `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

2) Copy env template and fill values:
   - `copy .env.example .env` (Windows)
   - set `MCP_TOKENS_JSON` and `GITHUB_TOKEN`

3) Run:
   - `.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload`

## MCP client config

See `mcp.json.example` for URL + Bearer header format.

## Notes

- For higher GitHub rate limits, use `GITHUB_TOKEN` (PAT) even in dev.
