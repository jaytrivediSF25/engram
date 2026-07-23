"""Condense a Claude Code transcript (.jsonl) into a chat tile."""

from __future__ import annotations

import json
from pathlib import Path

MAX_MSG_CHARS = 1500
MAX_TOTAL_CHARS = 12_000
MIN_CHARS = 200  # skip trivial sessions


def _text_of(content) -> str:
    """Extract plain text from a message content field (string or block list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def condense_transcript(path: str | Path) -> str | None:
    """Turn a session transcript into a compact chat record, or None if trivial."""
    lines: list[str] = []
    try:
        raw = Path(path).read_text()
    except OSError:
        return None

    for line in raw.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("isMeta") or entry.get("type") not in ("user", "assistant"):
            continue
        text = _text_of(entry.get("message", {}).get("content")).strip()
        if not text or text.startswith("<"):  # system-reminder / command wrappers
            continue
        if len(text) > MAX_MSG_CHARS:
            text = text[:MAX_MSG_CHARS] + " …[trimmed]"
        role = "User" if entry["type"] == "user" else "Assistant"
        lines.append(f"**{role}:** {text}")

    condensed = "\n\n".join(lines)
    if len(condensed) < MIN_CHARS:
        return None
    if len(condensed) > MAX_TOTAL_CHARS:
        # keep the opening and the (more recent) tail
        head, tail = condensed[:3000], condensed[-(MAX_TOTAL_CHARS - 3000) :]
        condensed = head + "\n\n…[middle of session trimmed]…\n\n" + tail
    return condensed
