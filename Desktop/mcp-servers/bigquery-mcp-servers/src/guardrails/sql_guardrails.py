from __future__ import annotations

import re

_MULTI_LINE_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_SINGLE_LINE_COMMENT = re.compile(r"(--|#).*$", re.MULTILINE)

# BigQuery identifier (dataset/table) validation: letters/numbers/underscore, starts with letter/underscore
_BQ_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,1023}$")


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
        raise ValueError(
            "Multiple statements are not allowed (possible script detected). Provide a single SELECT query."
        )


def require_bq_identifier(name: str, *, kind: str = "identifier") -> str:
    """
    Validate dataset/table identifiers to prevent SQL injection when we build INFORMATION_SCHEMA queries.
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"{kind} is required")
    n = name.strip()
    if not _BQ_IDENTIFIER_RE.match(n):
        raise ValueError(
            f"Invalid {kind} '{name}'. Only letters, numbers, underscore are allowed, "
            "and it must start with a letter or underscore."
        )
    return n


def region_information_schema_prefix(location: str | None) -> str:
    """
    Convert BigQuery job location into INFORMATION_SCHEMA region prefix.
    Examples:
      - 'europe-west2' -> 'region-europe-west2'
      - 'EU' -> 'region-eu'
      - 'US' -> 'region-us'
    """
    if not location:
        # Best practice: set BQ_LOCATION explicitly, but defaulting avoids crashes.
        return "region-us"
    return f"region-{location.lower()}"