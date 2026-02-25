# BigQuery MCP Server (Custom)

Remote MCP server (SSE) deployed on Cloud Run.

- Auth: `Authorization: Bearer <token>`
- BigQuery: read-only (SELECT-only enforced server-side)
- CI/CD: Cloud Build -> Artifact Registry -> Cloud Run

## Local run (dev)

1) Create a venv and install deps:
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`

2) Copy env template and fill values:
   - `cp .env.example .env`

3) Run:
   - `uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload`

## Deploy (CI/CD)

Cloud Build trigger runs `cloudbuild.yaml` which:

1) Builds docker image
2) Pushes to Artifact Registry
3) Deploys to Cloud Run

## Client config (Copilot / n8n)

See `mcp.json.example` for the URL + Bearer header format.
