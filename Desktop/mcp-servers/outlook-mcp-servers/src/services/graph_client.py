# src/services/graph_client.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import msal
from zoneinfo import ZoneInfo

from ..settings import Settings


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@dataclass(frozen=True)
class GraphToken:
    access_token: str


class GraphCalendarService:
    """
    Microsoft Graph calendar wrapper for /me/calendarView (delegated permissions).
    Uses MSAL device code flow for local testing.
    Caches tokens to disk to avoid repeated logins.
    """

    def __init__(
        self,
        *,
        tenant_id: str,
        client_id: str,
        scopes: list[str],
        token_cache_path: str,
        timeout_seconds: int = 20,
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._scopes = scopes
        self._cache_path = Path(token_cache_path)

        self._token_cache = msal.SerializableTokenCache()
        if self._cache_path.exists():
            self._token_cache.deserialize(self._cache_path.read_text(encoding="utf-8"))

        self._app = msal.PublicClientApplication(
            client_id=self._client_id,
            authority=f"https://login.microsoftonline.com/{self._tenant_id}",
            token_cache=self._token_cache,
        )

        self._http = httpx.Client(timeout=timeout_seconds)

    @classmethod
    def from_settings(cls, settings: Settings) -> "GraphCalendarService":
        scopes = [s.strip() for s in settings.ms_scopes.split() if s.strip()]
        return cls(
            tenant_id=settings.ms_tenant_id,
            client_id=settings.ms_client_id,
            scopes=scopes,
            token_cache_path=settings.ms_token_cache_path,
            timeout_seconds=20,
        )

    def close(self) -> None:
        try:
            self._http.close()
        except Exception:
            pass

    # -------------------------
    # Auth
    # -------------------------
    def _save_cache_if_changed(self) -> None:
        if self._token_cache.has_state_changed:
            self._cache_path.write_text(self._token_cache.serialize(), encoding="utf-8")

    def _acquire_token(self) -> GraphToken:
        accounts = self._app.get_accounts()
        result: Optional[dict[str, Any]] = None

        if accounts:
            result = self._app.acquire_token_silent(self._scopes, account=accounts[0])

        if not result:
            flow = self._app.initiate_device_flow(scopes=self._scopes)
            if "user_code" not in flow:
                raise RuntimeError(f"Failed to start device code flow: {flow}")

            # IMPORTANT: user must complete this once in browser
            # Print the message shown by Microsoft (contains verification URL + code)
            print(flow["message"])

            result = self._app.acquire_token_by_device_flow(flow)

        if not result or "access_token" not in result:
            raise RuntimeError(f"Failed to acquire Graph token: {result}")

        self._save_cache_if_changed()
        return GraphToken(access_token=result["access_token"])

    # -------------------------
    # Graph calls
    # -------------------------
    def _get(self, url: str, *, params: dict[str, Any] | None = None, tz: str | None = None) -> Any:
        token = self._acquire_token()
        headers = {"Authorization": f"Bearer {token.access_token}"}
        if tz:
            headers["Prefer"] = f'outlook.timezone="{tz}"'
        r = self._http.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    def list_meetings(
        self,
        start_iso: str,
        end_iso: str,
        timezone: str,
        max_events: int,
    ) -> List[Dict[str, Any]]:
        """
        Uses /me/calendarView to get events between start and end.
        """
        url = f"{GRAPH_BASE}/me/calendarView"
        params = {
            "startDateTime": start_iso,
            "endDateTime": end_iso,
            "$top": max_events,
            "$orderby": "start/dateTime",
            "$select": "subject,start,end,organizer,location,isOnlineMeeting,onlineMeeting,webLink",
        }
        data = self._get(url, params=params, tz=timezone)
        items = data.get("value", []) or []
        return [_normalize_event(e) for e in items]

    def next_meeting(self, within_days: int, timezone: str) -> Dict[str, Any]:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz=tz)
        start = now.isoformat()
        end = (now + timedelta(days=within_days)).isoformat()

        events = self.list_meetings(start, end, timezone, max_events=50)
        # pick first that starts after now
        for e in events:
            # start is a string; parse conservative
            start_s = (e.get("start") or {}).get("dateTime")
            if not start_s:
                continue
            try:
                start_dt = datetime.fromisoformat(start_s)
            except Exception:
                continue
            if start_dt >= now:
                return e

        return {"message": f"No upcoming meetings found within {within_days} days."}


def _normalize_event(e: dict[str, Any]) -> dict[str, Any]:
    org = e.get("organizer", {}) or {}
    org_email = ((org.get("emailAddress") or {}) if isinstance(org.get("emailAddress"), dict) else {}) or {}
    loc = e.get("location", {}) or {}

    start = e.get("start", {}) or {}
    end = e.get("end", {}) or {}

    online = e.get("onlineMeeting", {}) or {}
    return {
        "subject": e.get("subject"),
        "start": {"dateTime": start.get("dateTime"), "timeZone": start.get("timeZone")},
        "end": {"dateTime": end.get("dateTime"), "timeZone": end.get("timeZone")},
        "organizer": {"name": org_email.get("name"), "address": org_email.get("address")},
        "location": {"displayName": loc.get("displayName")},
        "isOnlineMeeting": e.get("isOnlineMeeting"),
        "onlineMeetingJoinUrl": online.get("joinUrl"),
        "webLink": e.get("webLink"),
    }