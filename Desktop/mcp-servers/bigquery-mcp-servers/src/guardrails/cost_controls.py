# src/guardrails/cost_controls.py
from __future__ import annotations


def enforce_estimated_bytes(*, estimated_bytes: int | None, max_bytes: int) -> None:
    """
    If the dry-run estimate exceeds max_bytes, fail fast.
    Note: dry-run is an estimate for bytes processed.
    """
    if estimated_bytes is None:
        return
    if max_bytes <= 0:
        return
    if estimated_bytes > max_bytes:
        raise ValueError(
            f"Query rejected: estimated bytes processed ({estimated_bytes}) exceeds cap ({max_bytes})."
        )


def clamp_rows(*, requested: int | None, default: int, hard_max: int) -> int:
    """
    Determine the max rows returned to the client.
    This does NOT change query cost, it only limits the returned payload size.
    """
    if requested is None:
        n = default
    else:
        n = requested

    if n <= 0:
        n = default

    if n > hard_max:
        n = hard_max

    return n