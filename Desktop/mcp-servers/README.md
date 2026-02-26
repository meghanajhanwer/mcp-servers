Latest mcp-servers -----

bigquery-mcp-servers--

Step 1 -
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
generate two token to replace it in bigquery-mcp-sserver/.env file

Step 2 Create a venv (Python 3.12) + install deps -
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip3 install -r requirements.txt

Step 3 Start the server locally
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload

curl.exe -i <http://localhost:8080/healthz>
curl.exe -i <http://localhost:8080/sse>
curl.exe -N -H "Authorization: Bearer NDYzS8VqeS4LMYr4g_BEfWHwg_yKHfbiefHIGvGxqOo" <http://localhost:8080/sse>

Deploy BigQuery MCP server to Cloud Run (Option 3: Cloud Build trigger)
A) One-time GCP setup (project-level)

Run these (replace project/region names as needed):

1) Set project + enable APIs
gcloud config set project your-mcp-demo-487412

gcloud services enable `
run.googleapis.com `
  cloudbuild.googleapis.com `
artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  bigquery.googleapis.com
2) Create Artifact Registry repo

Choose a region (example: europe-west2) and create repo (example: mcp-repo):

gcloud artifacts repositories create mcp-repo `
--repository-format=docker `
  --location=europe-west2 `
--description="MCP server images"
B) Runtime identity + permissions (Cloud Run service account)
3) Create runtime service account
gcloud iam service-accounts create mcp-runtime `
  --display-name="MCP Cloud Run runtime"
4) Grant BigQuery read-only access (project-wide, since you said that’s ok)
gcloud projects add-iam-policy-binding mcp-demo-487412 `
--member="serviceAccount:mcp-runtime@mcp-demo-487412.iam.gserviceaccount.com" `
  --role="roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding mcp-demo-487412 `
--member="serviceAccount:mcp-runtime@mcp-demo-487412.iam.gserviceaccount.com" `
  --role="roles/bigquery.dataViewer"
C) Tokens in Secret Manager (for Bearer auth)
5) Create a secret with JSON payload

Create a local file mcp-bq-tokens.json:

{"copilot-test":"<TOKEN1>","n8n-prod":"<TOKEN2>"}

Then:

gcloud secrets create mcp-bq-tokens --replication-policy="automatic"
gcloud secrets versions add mcp-bq-tokens --data-file="mcp-bq-tokens.json"
6) Allow runtime service account to read the secret
gcloud secrets add-iam-policy-binding mcp-bq-tokens `
--member="serviceAccount:mcp-runtime@mcp-demo-487412.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
D) Allow Cloud Build to deploy to Cloud Run
52850157736
Cloud Build runs as:
<PROJECT_NUMBER>@cloudbuild.gserviceaccount.com

Get your project number:

gcloud projects describe mcp-demo-487412 --format="value(projectNumber)"

Then grant Cloud Run deploy permissions:

$PN = (gcloud projects describe mcp-demo-487412 --format="value(projectNumber)")

gcloud projects add-iam-policy-binding mcp-demo-487412 `
--member="serviceAccount:$PN@cloudbuild.gserviceaccount.com" `
  --role="roles/run.admin"

gcloud iam service-accounts add-iam-policy-binding `
mcp-runtime@mcp-demo-487412.iam.gserviceaccount.com `
  --member="serviceAccount:$<PN@cloudbuild.gserviceaccount.com>" `
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding mcp-demo-487412 `
--member="serviceAccount:$PN@cloudbuild.gserviceaccount.com" `
  --role="roles/artifactregistry.writer"
