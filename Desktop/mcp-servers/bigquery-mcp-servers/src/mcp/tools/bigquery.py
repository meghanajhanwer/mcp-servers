# src/mcp/tools/bigquery.py
from __future__ import annotations

import anyio

from mcp.server.fastmcp import FastMCP

from ...guardrails.cost_controls import clamp_rows, enforce_estimated_bytes
from ...guardrails.sql_guardrails import normalize_sql, reject_multiple_statements
from ...services.bigquery_client import BigQueryService
from ...settings import Settings


def register_bigquery_tools(*, mcp: FastMCP, settings: Settings, bq_service: BigQueryService) -> None:
    @mcp.tool()
    async def bigquery_select(sql: str, max_rows: int | None = None) -> dict:
        """
        Run a READ-ONLY BigQuery query (SELECT only).

        Args:
            sql: SQL query string. Only SELECT queries are allowed.
            max_rows: Maximum rows returned to the client (server-enforced cap).
        """
        cleaned = normalize_sql(sql)
        reject_multiple_statements(cleaned)

        # 1) Dry run to validate and determine statement type + estimate bytes
        dry = await anyio.to_thread.run_sync(
            bq_service.dry_run,
            cleaned,
            cancellable=True,
        )

        stmt = (dry.statement_type or "").upper()
        if stmt != "SELECT":
            raise ValueError(f"Only SELECT queries are allowed. Detected statement_type={dry.statement_type!r}")

        # 2) Hard cost gate (fail fast before running)
        enforce_estimated_bytes(
            estimated_bytes=dry.total_bytes_processed,
            max_bytes=settings.bq_max_bytes_billed,
        )

        # 3) Execute SELECT with return-row cap
        effective_rows = clamp_rows(
            requested=max_rows,
            default=settings.bq_default_limit,
            hard_max=settings.bq_max_return_rows,
        )

        result = await anyio.to_thread.run_sync(
            bq_service.execute_select,
            cleaned,
            effective_rows,
            cancellable=True,
        )

        # Return a compact, verification-friendly payload
        return {
            "ok": True,
            "query": cleaned,
            "dry_run": {
                "statement_type": dry.statement_type,
                "total_bytes_processed": dry.total_bytes_processed,
            },
            "job": {
                "job_id": result.job_id,
                "location": result.location,
                "statement_type": result.statement_type,
                "total_bytes_processed": result.total_bytes_processed,
                "total_bytes_billed": result.total_bytes_billed,
            },
            "result": {
                "max_rows": effective_rows,
                "returned_rows": len(result.rows),
                "schema": result.schema,
                "rows": result.rows,
            },
        }