# src/settings.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
    mcp_tokens_json: str | None = Field(default=None, alias="MCP_TOKENS_JSON")
    mcp_tokens_secret_payload: str | None = Field(default=None, alias="MCP_TOKENS_SECRET_PAYLOAD")

    # Microsoft Graph / OAuth (Device Code)
    ms_tenant_id: str = Field(alias="MS_TENANT_ID")   # Directory (tenant) ID
    ms_client_id: str = Field(alias="MS_CLIENT_ID")   # Application (client) ID

    # Space-separated scopes (Graph delegated)
    # Recommended: "Calendars.Read offline_access"
    ms_scopes: str = Field(default="Calendars.Read offline_access", alias="MS_SCOPES")

    # Token cache file (persist refresh token for local testing)
    ms_token_cache_path: str = Field(default=".msal_token_cache.bin", alias="MS_TOKEN_CACHE_PATH")

    # Timezone for display / “today”
    user_timezone: str = Field(default="Europe/London", alias="USER_TIMEZONE")

    # Limits / guardrails
    max_days_range: int = Field(default=14, alias="OUTLOOK_MAX_DAYS_RANGE")
    max_events_return: int = Field(default=50, alias="OUTLOOK_MAX_EVENTS_RETURN")

    def docs_enabled(self) -> bool:
        return self.env.lower() not in {"prod", "production"}