# src/services/secrets.py
from __future__ import annotations

import json
import secrets as py_secrets
from dataclasses import dataclass
from typing import Dict

from fastapi import Request

from ..settings import Settings


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class TokenStore:
    token_to_label: Dict[str, str]

    @classmethod
    def from_settings(cls, settings: Settings) -> "TokenStore":
        label_to_token = _load_tokens_label_to_token(settings)
        token_to_label = {token: label for label, token in label_to_token.items()}
        if not token_to_label:
            raise RuntimeError("No MCP tokens configured. Provide MCP_TOKENS_JSON or MCP_TOKENS_SECRET_PAYLOAD.")
        return cls(token_to_label=token_to_label)

    def authenticate_request(self, request: Request) -> str:
        token = _extract_bearer_token(request)
        if not token:
            raise AuthError("Missing Bearer token")

        for known, label in self.token_to_label.items():
            if py_secrets.compare_digest(known, token):
                return label

        raise AuthError("Invalid token")


def _load_tokens_label_to_token(settings: Settings) -> Dict[str, str]:
    if settings.mcp_tokens_json:
        return _parse_tokens_json(settings.mcp_tokens_json)
    if settings.mcp_tokens_secret_payload:
        return _parse_tokens_json(settings.mcp_tokens_secret_payload)
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
        if isinstance(label, str) and isinstance(token, str):
            label = label.strip()
            token = token.strip()
            if label and token:
                cleaned[label] = token
    return cleaned


def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None