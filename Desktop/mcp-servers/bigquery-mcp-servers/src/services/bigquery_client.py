# src/services/bigquery_client.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from google.cloud import bigquery

from ..settings import Settings


@dataclass(frozen=True)
class DryRunResult:
    statement_type: str | None
    total_bytes_processed: int | None


@dataclass(frozen=True)
class QueryResult:
    job_id: str
    location: str | None
    statement_type: str | None
    total_bytes_processed: int | None
    total_bytes_billed: int | None
    schema: list[dict[str, Any]]
    rows: list[dict[str, Any]]


class BigQueryService:
    def __init__(self, *, client: bigquery.Client, location: str | None, max_bytes_billed: int) -> None:
        self._client = client
        self._location = location
        self._max_bytes_billed = max_bytes_billed

    @classmethod
    def from_settings(cls, settings: Settings) -> "BigQueryService":
        client = bigquery.Client(project=settings.bq_project_id)
        return cls(client=client, location=settings.bq_location, max_bytes_billed=settings.bq_max_bytes_billed)

    def dry_run(self, sql: str) -> DryRunResult:
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = self._client.query(sql, job_config=job_config, location=self._location)
        # Dry run completes immediately; stats available right away.
        return DryRunResult(
            statement_type=query_job.statement_type,
            total_bytes_processed=query_job.total_bytes_processed,
        )

    def execute_select(self, sql: str, max_rows: int) -> QueryResult:
        job_config = bigquery.QueryJobConfig(
            dry_run=False,
            use_query_cache=True,
            maximum_bytes_billed=self._max_bytes_billed,
        )

        query_job = self._client.query(sql, job_config=job_config, location=self._location)
        row_iter = query_job.result(max_results=max_rows)  # waits for completion

        schema = []
        try:
            for field in (row_iter.schema or []):
                schema.append(
                    {
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode,
                    }
                )
        except Exception:
            # Schema isn't critical; keep going
            schema = []

        rows: list[dict[str, Any]] = []
        for row in row_iter:
            # Row behaves like a mapping; convert and ensure JSON-safe values.
            as_dict = dict(row)
            rows.append(_json_safe(as_dict))

        return QueryResult(
            job_id=query_job.job_id,
            location=self._location,
            statement_type=query_job.statement_type,
            total_bytes_processed=query_job.total_bytes_processed,
            total_bytes_billed=query_job.total_bytes_billed,
            schema=schema,
            rows=rows,
        )


def _json_safe(value: Any) -> Any:
    """
    Convert BigQuery result values into JSON-serializable forms.
    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        # preserve precision
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, bytes):
        # Avoid large payloads; represent bytes safely
        return value.hex()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    # Fallback: safe string
    return str(value)