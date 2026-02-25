# src/guardrails/time_window.py
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def parse_iso_range(start_iso: str, end_iso: str) -> tuple[str, str]:
    if not start_iso or not end_iso:
        raise ValueError("start_iso and end_iso are required")

    # Validate parseability; keep original ISO for Graph
    try:
        datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    except Exception as e:
        raise ValueError(f"Invalid ISO datetime. Use e.g. 2026-02-25T09:00:00+00:00. Error: {e}") from e

    return start_iso, end_iso


def clamp_range_days(start_iso: str, end_iso: str, *, max_days: int) -> tuple[str, str]:
    s = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    e = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    if e <= s:
        raise ValueError("end_iso must be after start_iso")

    if (e - s) > timedelta(days=max_days):
        e = s + timedelta(days=max_days)
    return s.isoformat(), e.isoformat()


def today_range(timezone: str) -> tuple[str, str]:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz=tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()