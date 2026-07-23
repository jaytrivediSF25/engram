"""Security primitives: private-by-default storage and secret redaction.

engram stores condensed copies of your sessions on disk and replays them into
future Claude context. Two consequences follow, both handled here:

1. The store must not be readable by other users on the machine — it can
   contain proprietary project detail. `harden_path` enforces 0700 dirs / 0600
   files (no-op on Windows, which uses ACLs).
2. A secret typed into a session must not be persisted verbatim, or it would be
   replayed into every later session that mounts the window. `redact` scrubs
   common secret shapes before anything is written.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ── private-by-default storage ────────────────────────────────────────────

DIR_MODE = 0o700
FILE_MODE = 0o600


def harden_path(path: Path) -> None:
    """chmod a file (0600) or directory (0700). Silent no-op off POSIX."""
    if os.name != "posix":
        return
    try:
        mode = DIR_MODE if path.is_dir() else FILE_MODE
        os.chmod(path, mode)
    except OSError:
        pass


def secure_write_text(path: Path, text: str) -> None:
    """Atomically write `text` to `path` with 0600 perms (temp file + rename).

    Atomic so an interrupted write can never leave a half-written tile/anchor,
    and 0600 from creation so the secret window never briefly exists as
    world-readable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    harden_path(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, path)
    harden_path(path)


def harden_tree(root: Path) -> None:
    """Best-effort tighten perms on an existing store tree (for upgrades)."""
    if os.name != "posix" or not root.exists():
        return
    harden_path(root)
    for p in root.rglob("*"):
        harden_path(p)


# ── secret redaction ──────────────────────────────────────────────────────

# Each pattern captures a secret shape; the whole match is replaced with a
# marker so eviction/anchor math still sees roughly the same token count.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ANTHROPIC_KEY", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OPENAI_KEY", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GOOGLE_KEY", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("STRIPE_KEY", re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{20,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)),
    ("BEARER", re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{20,}")),
    # KEY=secret / "api_key": "secret" for env-ish assignments with a
    # secret-suggestive name and a long-enough value.
    ("ASSIGNMENT", re.compile(
        r"(?i)\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API[_\-]?KEY|ACCESS[_\-]?KEY|PRIVATE[_\-]?KEY)[A-Z0-9_]*)"
        r"(\s*[:=]\s*['\"]?)"
        r"([^\s'\"]{8,})"
    )),
]


def redact(text: str) -> str:
    """Replace credential-shaped substrings with `‹redacted:KIND›` markers."""
    if not text:
        return text
    for kind, pat in _PATTERNS:
        if kind == "BEARER":
            text = pat.sub(r"\1 ‹redacted:BEARER›", text)
        elif kind == "ASSIGNMENT":
            text = pat.sub(r"\1\2‹redacted:SECRET›", text)
        else:
            text = pat.sub(f"‹redacted:{kind}›", text)
    return text
