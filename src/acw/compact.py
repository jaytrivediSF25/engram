"""Anchor compaction via headless Claude Code (`claude -p`).

Runs on the user's Claude subscription — no API key or credits needed.
"""

from __future__ import annotations

import os
import subprocess
import sys

from .tokens import count_tokens

COMPACT_SYSTEM = """\
You compact the founding context of a software/work project into a pinned "anchor" \
summary that will be permanently prepended to an AI agent's context.

From the chat transcript(s) below, extract and condense:
- The project's goals and intended outcome
- Hard constraints (tech choices, budgets, deadlines, non-negotiables)
- Founding decisions and the reasons behind them
- Key domain facts an agent would need in every future session

Rules:
- Write dense, factual markdown. No preamble, no meta-commentary.
- Preserve concrete details (names, paths, numbers, choices) over narrative.
- Drop small talk, dead ends, and anything derivable later.
- Stay under {budget} tokens (~{chars} characters).
- Output ONLY the summary itself.\
"""

TIMEOUT_SECONDS = 300


class CompactionError(Exception):
    """Raised when the anchor could not be produced. Callers must not evict."""


def _run_claude(prompt: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "ACW_ACTIVE"}
    # ACW_ACTIVE is stripped so this headless session doesn't trigger our own
    # hooks and capture itself as a chat.
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=env,
        )
    except FileNotFoundError as e:
        raise CompactionError("`claude` not found on PATH") from e
    except subprocess.TimeoutExpired as e:
        raise CompactionError(f"claude -p timed out after {TIMEOUT_SECONDS}s") from e
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:300]
        raise CompactionError(f"claude -p failed (exit {result.returncode}): {detail}")
    summary = result.stdout.strip()
    if not summary:
        raise CompactionError("claude -p returned empty output")
    return summary


def compact(founding_text: str, model: str, anchor_budget: int) -> str:
    """Summarize `founding_text` into an anchor of at most `anchor_budget` tokens.

    Makes one retry with a tighter instruction if the first summary is over
    budget; returns the second attempt either way (best effort).
    Raises CompactionError on failure.
    """
    system = COMPACT_SYSTEM.format(budget=anchor_budget, chars=anchor_budget * 4)
    summary = _run_claude(f"{system}\n\n---\n\n{founding_text}")
    actual = count_tokens(summary)
    if actual > anchor_budget:
        print(
            f"acw: anchor summary was ~{actual} tokens (cap {anchor_budget}); retrying tighter",
            file=sys.stderr,
        )
        summary = _run_claude(
            f"{system}\n\nYour previous attempt (below) was ~{actual} tokens, over the "
            f"{anchor_budget}-token cap. Rewrite it tighter — keep only the most "
            f"load-bearing facts.\n\n---\n\n{summary}"
        )
    return summary
