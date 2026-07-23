"""Anchor compaction: condense founding chats into a pinned anchor via Claude."""

from __future__ import annotations

import sys

import anthropic

from .tokens import count_tokens, get_client

COMPACT_SYSTEM = """\
You compact the founding context of a software/work project into a pinned "anchor" \
summary that will be permanently prepended to an AI agent's context.

From the chat transcript(s) you are given, extract and condense:
- The project's goals and intended outcome
- Hard constraints (tech choices, budgets, deadlines, non-negotiables)
- Founding decisions and the reasons behind them
- Key domain facts an agent would need in every future session

Rules:
- Write dense, factual markdown. No preamble, no meta-commentary.
- Preserve concrete details (names, paths, numbers, choices) over narrative.
- Drop small talk, dead ends, and anything derivable later.
- Stay under {budget} tokens.\
"""

RETRY_NUDGE = (
    "Your previous summary was {actual} tokens, over the {budget}-token cap. "
    "Rewrite it tighter — keep only the most load-bearing facts."
)


class CompactionError(Exception):
    """Raised when the anchor could not be produced. Callers must not evict."""


def _call(model: str, system: str, messages: list[dict]) -> str:
    with get_client().messages.stream(
        model=model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system,
        messages=messages,
    ) as stream:
        final = stream.get_final_message()
    return "".join(b.text for b in final.content if b.type == "text").strip()


def compact(founding_text: str, model: str, anchor_budget: int) -> str:
    """Summarize `founding_text` into an anchor of at most `anchor_budget` tokens.

    Makes one retry with a tighter instruction if the first summary is over
    budget; returns the second attempt either way (best effort).
    Raises CompactionError on API failure.
    """
    system = COMPACT_SYSTEM.format(budget=anchor_budget)
    messages: list[dict] = [{"role": "user", "content": founding_text}]
    try:
        summary = _call(model, system, messages)
        actual = count_tokens(summary, model)
        if actual > anchor_budget:
            print(
                f"acw: anchor summary was {actual} tokens (cap {anchor_budget}); retrying tighter",
                file=sys.stderr,
            )
            messages += [
                {"role": "assistant", "content": summary},
                {"role": "user", "content": RETRY_NUDGE.format(actual=actual, budget=anchor_budget)},
            ]
            summary = _call(model, system, messages)
        return summary
    except anthropic.RateLimitError as e:
        raise CompactionError(f"rate limited by the Anthropic API: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise CompactionError(f"Anthropic API error ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise CompactionError(f"could not reach the Anthropic API: {e}") from e
