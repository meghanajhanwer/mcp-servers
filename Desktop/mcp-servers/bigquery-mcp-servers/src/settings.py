# src/settings.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Runtime configuration loaded from environment variables.
    In local dev, values can be provided via a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    env: str = Field(default="dev", alias="ENV")
    port: int = Field(default=8080, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # GCP / BigQuery
    gcp_project_id: str | None = Field(default=None, alias="GCP_PROJECT_ID")
    bq_project_id: str = Field(alias="BQ_PROJECT_ID")
    bq_location: str | None = Field(default=None, alias="BQ_LOCATION")

    # Guardrails / cost controls
    bq_max_bytes_billed: int = Field(default=5_000_000_000, alias="BQ_MAX_BYTES_BILLED")
    bq_default_limit: int = Field(default=500, alias="BQ_DEFAULT_LIMIT")
    bq_max_return_rows: int = Field(default=1000, alias="BQ_MAX_RETURN_ROWS")

    # MCP endpoint auth tokens
    # Option A (local): JSON string: {"copilot-test":"<token>","n8n-prod":"<token>"}
    mcp_tokens_json: str | None = Field(default=None, alias="MCP_TOKENS_JSON")

    # Option B (prod): secret injected as an env var payload
    # (Cloud Run: --set-secrets MCP_TOKENS_SECRET_PAYLOAD=<secret>:latest)
    mcp_tokens_secret_payload: str | None = Field(default=None, alias="MCP_TOKENS_SECRET_PAYLOAD")

    # Option C (fallback): pull from Secret Manager by name/version
    mcp_tokens_secret_name: str | None = Field(default=None, alias="MCP_TOKENS_SECRET_NAME")
    mcp_tokens_secret_version: str = Field(default="latest", alias="MCP_TOKENS_SECRET_VERSION")

    # Auth behavior
    allow_query_param_token: bool = Field(default=False, alias="ALLOW_QUERY_PARAM_TOKEN")

    @property
    def is_prod(self) -> bool:
        return self.env.lower() in {"prod", "production"}

    def docs_enabled(self) -> bool:
        # Keep docs off in prod by default
        return not self.is_prod