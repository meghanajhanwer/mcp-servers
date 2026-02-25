# src/guardrails/limits.py
from __future__ import annotations


def clamp_int(value: int | None, *, default: int, min_value: int, max_value: int) -> int:
    if value is None:
        v = default
    else:
        v = int(value)

    if v < min_value:
        v = min_value
    if v > max_value:
        v = max_value
    return v