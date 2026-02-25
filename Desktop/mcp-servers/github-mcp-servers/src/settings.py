# src/settings.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Runtime configuration loaded from environment variables.
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

    # MCP endpoint auth tokens
    # Option A (local): JSON string: {"copilot-test":"<token>","n8n-prod":"<token>"}
    mcp_tokens_json: str | None = Field(default=None, alias="MCP_TOKENS_JSON")

    # Option B (prod): secret injected as an env var payload
    # (Cloud Run: --set-secrets MCP_TOKENS_SECRET_PAYLOAD=<secret>:latest)
    mcp_tokens_secret_payload: str | None = Field(default=None, alias="MCP_TOKENS_SECRET_PAYLOAD")

    # GitHub API config
    github_api_base_url: str = Field(default="https://api.github.com", alias="GITHUB_API_BASE_URL")
    github_user_agent: str = Field(default="mcp-github-server/0.1", alias="GITHUB_USER_AGENT")
    github_timeout_seconds: int = Field(default=15, alias="GITHUB_TIMEOUT_SECONDS")

    # GitHub credentials (PAT or GitHub App token)
    # For MVP, use a PAT in local .env: GITHUB_TOKEN=...
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    # Optional: injected secret payload
    github_token_secret_payload: str | None = Field(default=None, alias="GITHUB_TOKEN_SECRET_PAYLOAD")

    # Guardrails / limits
    github_max_repos_scan: int = Field(default=25, alias="GITHUB_MAX_REPOS_SCAN")
    github_max_commits_return: int = Field(default=20, alias="GITHUB_MAX_COMMITS_RETURN")
    github_allowed_repos: str | None = Field(default=None, alias="GITHUB_ALLOWED_REPOS")

    # Docs in dev only
    def docs_enabled(self) -> bool:
        return self.env.lower() not in {"prod", "production"}