# Architecture

engram implements an **anchored sliding window** over Claude Code sessions.
This document explains the data model, the eviction algorithm, the hook
lifecycle, and the failure model.

## The tile model

```
window_tokens (total budget)
├── anchor_tokens          → the pinned anchor (tile 0)
└── the rest               → the sliding window of chat tiles
```

- A **chat tile** is one captured session: `{id, created_at, tokens, content}`.
  Content is the condensed transcript — user and assistant text, tool noise
  stripped, long messages trimmed.
- The **anchor** is a single markdown document produced *once*, by compacting
  the earliest evicted sessions. It holds goals, constraints, and founding
  decisions — the things that never stop being true.

## Eviction algorithm

On every capture (`store.add_chat`):

1. Count the new chat's tokens and append it as the newest tile.
2. While `sum(tile tokens) > window_tokens − anchor_tokens`, mark the oldest
   tile for eviction — but **never the newest** (the window must always hold
   at least the most recent session).
3. If no anchor exists yet, the marked tiles are the project's *founding
   sessions*: concatenate them and compact via `claude -p` into `anchor.md`.
   Only after the anchor is written are the tiles deleted.
4. If an anchor already exists, marked tiles are simply deleted — the anchor
   is pinned and never revisited.

Step 3's ordering is the crash-safety property: the founding content is
deleted only after its summary durably exists on disk.

## Hook lifecycle

```
engram                          # sets ENGRAM_ACTIVE=1, execs claude
 ├─ SessionStart hook           # engram hook-session-start
 │    reads {cwd} from stdin
 │    prints additionalContext = anchor + tiles
 ├─ ... you work ...
 └─ SessionEnd hook             # engram hook-session-end
      reads {cwd, transcript_path} from stdin
      condenses transcript → add_chat → evict/compact as needed
```

Both hooks return immediately when `ENGRAM_ACTIVE` is unset, which is why a
plain `claude` session is completely unaffected. The compaction subprocess
strips `ENGRAM_ACTIVE` from its own environment so the headless `claude -p`
session can never recursively capture itself.

## Token accounting

Budgets use a `len(text) // 4` estimator. Eviction only needs budgets to be
approximately right, and an estimator keeps engram fully offline — no metered
counting endpoint, no API key.

## Failure model

| Failure | Behavior |
|---|---|
| `claude -p` fails / times out / offline | `CompactionError` → eviction aborted, tiles kept, retried on next capture |
| Transcript unreadable or trivial (<200 chars) | Session skipped, nothing stored |
| Malformed `~/.claude/settings.json` at install | Installer aborts before writing anything |
| Anchor summary over budget | One tighter rewrite attempt, then best-effort accept |

The invariant behind all of these: **no code path may lose a chat.**
