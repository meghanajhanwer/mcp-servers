# src/guardrails/sql_guardrails.py
from __future__ import annotations

import re


_MULTI_LINE_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_SINGLE_LINE_COMMENT = re.compile(r"(--|#).*$", re.MULTILINE)


def normalize_sql(sql: str) -> str:
    """
    Normalize SQL: strip comments and whitespace.
    This is NOT a full SQL parser; the real gate is BigQuery dry-run statement_type.
    """
    if sql is None:
        raise ValueError("SQL is required")

    s = sql.strip()
    if not s:
        raise ValueError("SQL is empty")

    # remove /* ... */ comments
    s = re.sub(_MULTI_LINE_COMMENT, "", s)
    # remove -- and # comments
    s = re.sub(_SINGLE_LINE_COMMENT, "", s)

    s = s.strip()
    if not s:
        raise ValueError("SQL is empty after removing comments")

    return s


def reject_multiple_statements(sql: str) -> None:
    """
    Reject obvious multi-statement inputs. BigQuery scripts can run multiple statements.
    We allow at most ONE trailing semicolon.
    """
    s = sql.strip()

    # Allow trailing semicolons; remove them
    while s.endswith(";"):
        s = s[:-1].rstrip()

    # If any other semicolon remains, assume multiple statements
    if ";" in s:
        raise ValueError("Multiple statements are not allowed (possible script detected). Provide a single SELECT query.")