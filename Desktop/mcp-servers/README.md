MCP-SERVER setup -

For Local testing -


Step 1 - create a token
python -c "import secrets; print(secrets.token_urlsafe(32))"
 for each service connection we need token


Step 2 Create a venv (Python 3.12) + install deps -

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip3 install -r requirements.txt

Step 3 Start the server locally -

uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload


curl.exe -i <http://localhost:8080/healthz>

curl.exe -i <http://localhost:8080/sse>

curl.exe -N -H "Authorization: Bearer NDYzS8VqeS4LMYr4g_BEfWHwg_yKHfbiefHIGvGxqOo" <http://localhost:8080/sse>

Deploy BigQuery MCP server to Cloud Run (Option 3: Cloud Build trigger)

One-time GCP setup (project-level)

1) Set project + enable APIs

gcloud config set project your-mcp-demo-487412

gcloud services enable `
run.googleapis.com `
  cloudbuild.googleapis.com `
artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  bigquery.googleapis.com

2) Create Artifact Registry repo

gcloud artifacts repositories create mcp-repo `
--repository-format=docker `
  --location=europe-west2 `
--description="MCP server images"


Runtime identity + permissions (Cloud Run service account)

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


Allow Cloud Build to deploy to Cloud Run
gcloud builds submit --config cloudbuild.yaml .

for proxy url -

gcloud run services proxy bigquery-mcp-tool --region europe-west2 --port 9090


Set 'role/run.invoker permission'
$PROJECT_ID = ""
$REGION     = "europe-west2"
$SERVICE    = "bigquery-mcp-tool"
$SA_EMAIL   = ""   # change to your SA

gcloud run services add-iam-policy-binding $SERVICE `
  --region $REGION `
--member "serviceAccount:$SA_EMAIL" `
  --role "roles/run.invoker"
