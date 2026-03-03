from __future__ import annotations

import anyio
from mcp.server.fastmcp import FastMCP

from ...guardrails.cost_controls import clamp_rows, enforce_estimated_bytes
from ...guardrails.sql_guardrails import (
    normalize_sql,
    reject_multiple_statements,
    require_bq_identifier,
    region_information_schema_prefix,
)
from ...services.bigquery_client import BigQueryService
from ...settings import Settings


async def _run_select(
    *,
    settings: Settings,
    bq_service: BigQueryService,
    sql: str,
    max_rows: int | None = None,
) -> dict:
    """
    Shared runner for all read-only SELECT queries (including metadata queries).
    Applies: normalize -> single statement -> dry run -> SELECT-only -> cost gate -> execute.
    """
    cleaned = normalize_sql(sql)
    reject_multiple_statements(cleaned)

    # Dry run
    dry = await anyio.to_thread.run_sync(bq_service.dry_run, cleaned, cancellable=True)

    stmt = (dry.statement_type or "").upper()
    if stmt != "SELECT":
        raise ValueError(f"Only SELECT queries are allowed. Detected statement_type={dry.statement_type!r}")

    # Cost gate
    enforce_estimated_bytes(
        estimated_bytes=dry.total_bytes_processed,
        max_bytes=settings.bq_max_bytes_billed,
    )

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


def register_bigquery_tools(*, mcp: FastMCP, settings: Settings, bq_service: BigQueryService) -> None:
    @mcp.tool()
    async def bigquery_select(sql: str, max_rows: int | None = None) -> dict:
        """
        Run a READ-ONLY BigQuery query (SELECT only).
        """
        return await _run_select(settings=settings, bq_service=bq_service, sql=sql, max_rows=max_rows)

    @mcp.tool()
    async def bigquery_list_datasets(max_rows: int | None = 500) -> dict:
        """
        List datasets in the configured project (via INFORMATION_SCHEMA.SCHEMATA).

        Note: This depends on BQ_LOCATION being correct (europe-west2 in your case).
        """
        region_prefix = region_information_schema_prefix(settings.bq_location)

        sql = f"""
        SELECT schema_name
        FROM `{region_prefix}`.INFORMATION_SCHEMA.SCHEMATA
        ORDER BY schema_name
        """

        out = await _run_select(settings=settings, bq_service=bq_service, sql=sql, max_rows=max_rows)

        # Also provide a simplified list for convenience
        datasets = [r.get("schema_name") for r in out["result"]["rows"] if "schema_name" in r]
        out["datasets"] = datasets
        out["project"] = settings.bq_project_id
        out["bq_location"] = settings.bq_location
        return out

    @mcp.tool()
    async def bigquery_list_tables(dataset: str, max_rows: int | None = 500) -> dict:
        """
        List tables/views in a dataset (via INFORMATION_SCHEMA.TABLES).
        """
        ds = require_bq_identifier(dataset, kind="dataset")

        sql = f"""
        SELECT table_name, table_type
        FROM `{settings.bq_project_id}.{ds}`.INFORMATION_SCHEMA.TABLES
        ORDER BY table_name
        """

        out = await _run_select(settings=settings, bq_service=bq_service, sql=sql, max_rows=max_rows)

        tables = [
            {"table_name": r.get("table_name"), "table_type": r.get("table_type")}
            for r in out["result"]["rows"]
            if "table_name" in r
        ]
        out["dataset"] = ds
        out["tables"] = tables
        out["project"] = settings.bq_project_id
        return out