# src/services/secrets.py
from __future__ import annotations

import json
import secrets as py_secrets
from dataclasses import dataclass
from typing import Dict, Tuple

from fastapi import Request
from google.cloud import secretmanager

from ..settings import Settings


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class TokenStore:
    """
    Stores a mapping of token_value -> token_label for validation and auditing.
    """
    token_to_label: Dict[str, str]

    @classmethod
    def from_settings(cls, settings: Settings) -> "TokenStore":
        token_map_label_to_token = load_tokens_label_to_token(settings)
        token_to_label = {token: label for label, token in token_map_label_to_token.items()}
        if not token_to_label:
            raise RuntimeError("No MCP tokens configured. Provide MCP_TOKENS_JSON or a Secret Manager secret.")
        return cls(token_to_label=token_to_label)

    def authenticate_request(self, request: Request) -> str:
        """
        Validate Bearer token from Authorization header (preferred),
        optionally from query param (?access_token=) if enabled.
        Returns the token label if valid.
        """
        token = _extract_bearer_token(request, allow_query_param=request.app.state.settings.allow_query_param_token) \
            if hasattr(request.app.state, "settings") else _extract_bearer_token(request, allow_query_param=False)

        # If app.state.settings isn't set (very early), fallback to header-only
        if token is None:
            token = _extract_bearer_token(request, allow_query_param=False)

        if not token:
            raise AuthError("Missing Bearer token")

        # Constant-time comparison against known tokens
        for known, label in self.token_to_label.items():
            if py_secrets.compare_digest(known, token):
                return label

        raise AuthError("Invalid token")


def load_tokens_label_to_token(settings: Settings) -> Dict[str, str]:
    """
    Load tokens as JSON mapping {label: token}.
    Priority:
      1) MCP_TOKENS_JSON (local)
      2) MCP_TOKENS_SECRET_PAYLOAD (env injected secret payload)
      3) Secret Manager lookup using MCP_TOKENS_SECRET_NAME + version
    """
    if settings.mcp_tokens_json:
        return _parse_tokens_json(settings.mcp_tokens_json)

    if settings.mcp_tokens_secret_payload:
        return _parse_tokens_json(settings.mcp_tokens_secret_payload)

    if settings.mcp_tokens_secret_name:
        payload = _read_secret_payload(
            project_id=settings.gcp_project_id or settings.bq_project_id,
            secret_name=settings.mcp_tokens_secret_name,
            version=settings.mcp_tokens_secret_version,
        )
        return _parse_tokens_json(payload)

    return {}


def _parse_tokens_json(payload: str) -> Dict[str, str]:
    try:
        data = json.loads(payload)
    except Exception as e:
        raise RuntimeError(f"Failed to parse MCP tokens JSON: {e}") from e

    if not isinstance(data, dict):
        raise RuntimeError("MCP tokens must be a JSON object mapping {label: token}")

    cleaned: Dict[str, str] = {}
    for label, token in data.items():
        if not isinstance(label, str) or not isinstance(token, str):
            continue
        label = label.strip()
        token = token.strip()
        if label and token:
            cleaned[label] = token

    return cleaned


def _read_secret_payload(*, project_id: str, secret_name: str, version: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"
    resp = client.access_secret_version(request={"name": name})
    return resp.payload.data.decode("utf-8")


def _extract_bearer_token(request: Request, *, allow_query_param: bool) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth:
        parts = auth.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()

    if allow_query_param:
        qp = request.query_params.get("access_token")
        if qp:
            return qp.strip()

    return None