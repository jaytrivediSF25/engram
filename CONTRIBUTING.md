# Contributing to acw

Thanks for your interest! acw is small on purpose — a pinned anchor, a sliding
window, and two Claude Code hooks. Contributions that keep it simple are the
most likely to land.

## Setup

```sh
git clone https://github.com/jaytrivediSF25/acw.git
cd acw
uv sync
uv run pytest
```

To try your changes live:

```sh
./install.sh    # installs your working copy as an editable tool
```

## Layout

```
src/acw/
├── cli.py       # argparse subcommands + the two hook entry points
├── store.py     # tile storage, budgets, eviction, anchor pinning
├── capture.py   # transcript (.jsonl) → condensed chat tile
├── compact.py   # founding chats → anchor, via headless `claude -p`
└── tokens.py    # chars/4 token estimator
```

## Ground rules

- **Tests must pass offline.** The eviction/anchor logic is tested with the
  counter and compactor injected as stubs — keep it that way.
- **The anchor is sacred.** Once built, nothing may mutate or evict it except
  an explicit `acw add --anchor` or `acw reset`.
- **Never lose a chat.** Any failure (compaction, parsing, network) must
  degrade to "chat stored, eviction deferred" — not data loss.
- **Plain `claude` stays untouched.** The hooks must remain inert without
  `ACW_ACTIVE`.

## Sending changes

1. Fork, branch, make the change
2. `uv run pytest` — add a test for any behavior change
3. Open a PR with a short description of *why*

Bug reports with a failing transcript or `acw status` output are gold.
