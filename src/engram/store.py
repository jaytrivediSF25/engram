"""Per-project storage and the anchored sliding-window eviction logic."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .secure import harden_path, harden_tree, redact, secure_write_text

DEFAULT_WINDOW_TOKENS = 50_000
DEFAULT_ANCHOR_TOKENS = 10_000
DEFAULT_MODEL = "claude-opus-4-8"

ROOT = Path.home() / ".engram" / "projects"


def store_dir_for(project_path: str | Path) -> Path:
    digest = hashlib.sha1(str(Path(project_path).resolve()).encode()).hexdigest()[:12]
    return ROOT / digest


@dataclass
class Chat:
    id: int
    created_at: str
    tokens: int
    content: str

    @property
    def filename(self) -> str:
        return f"{self.id:04d}.json"


@dataclass
class AddResult:
    chat: Chat
    evicted: list[Chat] = field(default_factory=list)
    anchor_built: bool = False


class StoreNotFound(Exception):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.chats_dir = root / "chats"
        self.config = json.loads((root / "config.json").read_text())
        self.state = json.loads((root / "state.json").read_text())

    # ── creation / lookup ────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        project_path: str | Path,
        window_tokens: int = DEFAULT_WINDOW_TOKENS,
        anchor_tokens: int = DEFAULT_ANCHOR_TOKENS,
        model: str = DEFAULT_MODEL,
    ) -> "Store":
        if anchor_tokens >= window_tokens:
            raise ValueError("anchor_tokens must be smaller than window_tokens")
        root = store_dir_for(project_path)
        (root / "chats").mkdir(parents=True, exist_ok=True)
        # Lock down ~/.engram, ~/.engram/projects, the store, and chats/ to 0700
        # so no other user on the machine can read captured project detail.
        for d in (ROOT.parent, ROOT, root, root / "chats"):
            harden_path(d)
        config = {
            "project_path": str(Path(project_path).resolve()),
            "window_tokens": window_tokens,
            "anchor_tokens": anchor_tokens,
            "model": model,
        }
        secure_write_text(root / "config.json", json.dumps(config, indent=2))
        state_path = root / "state.json"
        if not state_path.exists():
            secure_write_text(
                state_path,
                json.dumps({"next_id": 1, "anchor_built": False, "anchor_tokens_actual": 0}),
            )
        return cls(root)

    @classmethod
    def load(cls, project_path: str | Path) -> "Store":
        root = store_dir_for(project_path)
        if not (root / "config.json").exists():
            raise StoreNotFound(str(project_path))
        harden_tree(root)  # keep perms tight even for stores made by older versions
        return cls(root)

    @classmethod
    def load_or_create(cls, project_path: str | Path) -> "Store":
        try:
            return cls.load(project_path)
        except StoreNotFound:
            return cls.create(project_path)

    # ── accessors ────────────────────────────────────────────────────────

    @property
    def model(self) -> str:
        return self.config["model"]

    @property
    def window_tokens(self) -> int:
        return self.config["window_tokens"]

    @property
    def anchor_budget(self) -> int:
        return self.config["anchor_tokens"]

    @property
    def sliding_budget(self) -> int:
        return self.window_tokens - self.anchor_budget

    @property
    def anchor(self) -> str | None:
        path = self.root / "anchor.md"
        return path.read_text() if path.exists() else None

    def chats(self) -> list[Chat]:
        out = []
        for path in sorted(self.chats_dir.glob("*.json")):
            out.append(Chat(**json.loads(path.read_text())))
        return out

    def sliding_tokens(self) -> int:
        return sum(c.tokens for c in self.chats())

    # ── mutation ─────────────────────────────────────────────────────────

    def _save_state(self) -> None:
        secure_write_text(self.root / "state.json", json.dumps(self.state))

    def _write_chat(self, chat: Chat) -> None:
        secure_write_text(self.chats_dir / chat.filename, json.dumps(chat.__dict__))

    def set_anchor(self, text: str, tokens: int) -> None:
        secure_write_text(self.root / "anchor.md", text)
        self.state["anchor_built"] = True
        self.state["anchor_tokens_actual"] = tokens
        self._save_state()

    def add_chat(self, content: str, counter, compactor) -> AddResult:
        """Append a chat, evicting oldest tiles past the sliding budget.

        `counter(text, model) -> int` and
        `compactor(founding_text, model, anchor_budget) -> str` are injected so
        tests run without the network. The first eviction event compacts the
        evicted founding chats into the pinned anchor; the anchor is never
        touched afterwards. If compaction fails, nothing is evicted and the
        error propagates (the new chat is still stored).
        """
        content = redact(content)  # scrub credential-shaped strings before storing
        chat = Chat(
            id=self.state["next_id"],
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            tokens=counter(content, self.model),
            content=content,
        )
        self._write_chat(chat)
        self.state["next_id"] += 1
        self._save_state()

        # Pick eviction candidates, oldest first, but never the newest chat.
        chats = self.chats()
        total = sum(c.tokens for c in chats)
        evict: list[Chat] = []
        while total > self.sliding_budget and len(chats) - len(evict) > 1:
            oldest = chats[len(evict)]
            evict.append(oldest)
            total -= oldest.tokens

        result = AddResult(chat=chat, evicted=evict)
        if not evict:
            return result

        if not self.state["anchor_built"]:
            founding = "\n\n---\n\n".join(c.content for c in evict)
            summary = compactor(founding, self.model, self.anchor_budget)  # may raise
            self.set_anchor(summary, counter(summary, self.model))
            result.anchor_built = True

        for c in evict:
            (self.chats_dir / c.filename).unlink()
        return result

    def reset(self) -> None:
        shutil.rmtree(self.root)
