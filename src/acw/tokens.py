"""Token estimation — no API required.

Budgets only need to be approximately right for eviction math, so we use the
standard ~4 chars/token heuristic instead of a metered counting endpoint.
"""

from __future__ import annotations


def count_tokens(text: str, model: str | None = None) -> int:
    if not text.strip():
        return 0
    return max(1, len(text) // 4)
