# src/mcp/tools/outlook.py
from __future__ import annotations

import anyio
from mcp.server.fastmcp import FastMCP

from ...guardrails.time_window import parse_iso_range, today_range, clamp_range_days
from ...guardrails.limits import clamp_int
from ...services.graph_client import GraphCalendarService
from ...settings import Settings


def register_outlook_tools(*, mcp: FastMCP, settings: Settings, graph_service: GraphCalendarService) -> None:
    @mcp.tool()
    async def outlook_today_meetings() -> dict:
        """
        Returns today's meetings (calendarView) for the signed-in user.
        """
        start_dt, end_dt = today_range(settings.user_timezone)

        events = await anyio.to_thread.run_sync(
            graph_service.list_meetings,
            start_dt,
            end_dt,
            settings.user_timezone,
            settings.max_events_return,
            cancellable=True,
        )
        return {"ok": True, "range": {"start": start_dt, "end": end_dt}, "count": len(events), "events": events}

    @mcp.tool()
    async def outlook_meetings(start_iso: str, end_iso: str, max_events: int | None = None) -> dict:
        """
        Returns meetings within [start_iso, end_iso] for the signed-in user.
        ISO example: 2026-02-25T09:00:00+00:00
        """
        start_dt, end_dt = parse_iso_range(start_iso, end_iso)

        # Guardrail: clamp max range
        start_dt, end_dt = clamp_range_days(start_dt, end_dt, max_days=settings.max_days_range)

        limit = clamp_int(max_events, default=settings.max_events_return, min_value=1, max_value=settings.max_events_return)

        events = await anyio.to_thread.run_sync(
            graph_service.list_meetings,
            start_dt,
            end_dt,
            settings.user_timezone,
            limit,
            cancellable=True,
        )
        return {"ok": True, "range": {"start": start_dt, "end": end_dt}, "count": len(events), "events": events}

    @mcp.tool()
    async def outlook_next_meeting(within_days: int = 7) -> dict:
        """
        Returns the next upcoming meeting within N days (default 7).
        """
        within_days = clamp_int(within_days, default=7, min_value=1, max_value=settings.max_days_range)

        next_event = await anyio.to_thread.run_sync(
            graph_service.next_meeting,
            within_days,
            settings.user_timezone,
            cancellable=True,
        )
        return {"ok": True, "within_days": within_days, "next": next_event}