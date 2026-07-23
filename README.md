> Persistent project memory for Claude Code.

# engram

*An engram is the physical trace a memory leaves in the brain. This one lives on your disk.*

[![CI](https://github.com/jaytrivediSF25/engram/actions/workflows/ci.yml/badge.svg)](https://github.com/jaytrivediSF25/engram/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg)](https://www.python.org)
[![Claude Code](https://img.shields.io/badge/works%20with-Claude%20Code-D97757.svg)](https://claude.com/claude-code)
[![No API key](https://img.shields.io/badge/API%20key-not%20needed-success.svg)](#how-it-works)

**engram gives Claude Code long-term project memory that never forgets why the project exists.**

Every session opens knowing your project's founding goals, constraints, and decisions — plus your most recent sessions at full fidelity. Runs entirely on your Claude subscription. No API key, no credits, no config.

```
┌─────────────┬────────────┬────────────┬────────────┬────────────┐
│   Anchor    │  Chat n-3  │  Chat n-2  │  Chat n-1  │   Chat n   │
│  original   │   oldest   │            │            │   newest   │
│   context   │            │            │            │            │
└─────────────┴────────────┴────────────┴────────────┴────────────┘
    pinned     ────── sliding window: oldest evicts as new ──────▶
               ────── chats arrive ──────────────────────────────▶
```

## Highlights

- **Pinned anchor** — the sessions where you planned the project are compacted *once* into a permanent summary of goals, constraints, and founding decisions. It is never evicted, no matter how long the project runs.
- **Sliding window** — recent sessions stay verbatim, token-budgeted; the oldest tile drops off as new sessions arrive.
- **Fully automatic** — context injects at session start, the session is captured at exit. You just use Claude.
- **Opt-in per session** — `engram` gets the window; plain `claude` is completely untouched.
- **Zero API cost** — compaction runs through headless `claude -p` on your existing subscription.
- **Per-project** — every folder gets its own anchor and window.
- **Secure by default** — secrets are scrubbed before capture, the store is `0700`/`0600`, writes are atomic, and compaction treats session text as untrusted data. See [SECURITY.md](SECURITY.md).

## Quick start

```sh
git clone https://github.com/jaytrivediSF25/engram.git
cd engram
./install.sh
```

Then, from any project:

```sh
cd your-project
engram
```

That's it. Work, quit, come back tomorrow, run `engram` again — the new session already knows where you left off *and* why the project exists.

## What it looks like

Day one — plan the project:

```console
$ cd shoplite && engram
engram: no context for this project yet — this session will seed it

> Let's plan: offline-first inventory tracker, Raspberry Pi at the register,
> SQLite only, $2k budget, Q3 deadline. Flask over Node — team knows Flask.
```

Weeks later — the planning session has long since slid out of the window, but the new session still opens knowing:

```console
$ engram status
anchor  : built — 161/10000 tokens
sliding : 31240/40000 tokens across 4 chat(s)

$ engram
> where were we?

⏺ Per the project anchor: shoplite is an offline-first inventory tracker
  (Pi + SQLite, $2k budget, Q3, USB barcode scanners non-negotiable).
  Last session we finished the HID scanner debouncing — next up was the
  offline sync queue.
```

Want to see eviction + anchor-building happen in seconds? Run the miniature demo:

```sh
make demo    # tiny budgets, three simulated sessions, watch the anchor get built
```

## Why this exists

Two pure strategies for long-running project context, two failure modes:

| Strategy | Keeps recent detail | Remembers why the project exists |
|---|:---:|:---:|
| Sliding window | ✅ verbatim | ❌ founding context ages out |
| Full compaction | ❌ flattened into a summary | ✅ |
| **Anchored sliding window** | ✅ verbatim | ✅ pinned anchor |

A plain sliding window eventually evicts the sessions where you made the decisions that define the project. Full compaction keeps them, but grinds your recent work into lossy summary. engram spends exactly one tile of budget on a compacted anchor and keeps everything else at full fidelity.

## How it works

```
 engram
     │
     ▼
┌────────────────────┐   SessionStart hook   ┌──────────────────────┐
│    Claude Code     │ ◀──────────────────── │  anchor + chat tiles │
│     (session)      │                       │   ~/.engram/projects/   │
│                    │   SessionEnd hook     │                      │
│      you quit ─────┼─────────────────────▶ │  transcript captured │
└────────────────────┘                       │   as newest tile     │
                                             └──────────┬───────────┘
                          over budget? evict oldest ────┘
                          first eviction? compact founding chats
                          into the pinned anchor via `claude -p`
```

1. `engram` launches Claude Code with `ENGRAM_ACTIVE=1`. The installed SessionStart/SessionEnd hooks are **inert without it** — plain `claude` never touches engram.
2. At start, the hook injects `[anchor + recent chats]` into the session's context.
3. At exit, the session transcript is condensed and stored as the newest tile.
4. When the sliding budget overflows, the oldest tile evicts. The **first** eviction sends the founding sessions through headless `claude -p`, which writes the anchor: goals, constraints, decisions. After that the anchor is pinned forever; later evictions just drop.
5. If compaction ever fails (offline, etc.), nothing is lost — eviction is deferred and retried next session.

## Commands

| Command | What it does |
|---|---|
| `engram [args…]` | Launch Claude Code with the anchored window (extra args pass through) |
| `engram status` | Show tiles, token counts, budget usage |
| `engram context` | Print the anchor + recent chats (`--json` for machines) |
| `engram add` | Manually store a chat (stdin, `--text`, `--file`) |
| `engram add --anchor` | Force content directly into the pinned anchor slot |
| `engram init` | Set per-project budgets up front |
| `engram reset` | Delete this project's store |

## Configuration

Budgets are per-project, set at `engram init` (or defaulted on first use):

```sh
engram init \
  --window-tokens 50000 \   # total window budget (default)
  --anchor-tokens 10000     # anchor's slice — one tile of five (default)
```

## File layout

```
~/.engram/projects/<hash-of-project-path>/
├── config.json     # budgets + project path
├── anchor.md       # the pinned, compacted founding context
├── chats/
│   ├── 0007.json   # sliding tiles: {id, created_at, tokens, content}
│   └── 0008.json
└── state.json
```

Everything is plain text on your disk. Read it, edit it, delete it.

## engram vs. alternatives

| | engram | CLAUDE.md | Built-in compaction | Memory MCP servers |
|---|:---:|:---:|:---:|:---:|
| Automatic (no hand-writing) | ✅ | ❌ | ✅ | varies |
| Survives across sessions | ✅ | ✅ | ❌ | ✅ |
| Founding context can never age out | ✅ | ✅ | ❌ | ❌ |
| Recent sessions kept verbatim | ✅ | ❌ | ❌ | ❌ |
| Bounded, predictable token cost | ✅ | ❌ | ✅ | ❌ |
| Zero setup per project | ✅ | ❌ | ✅ | ❌ |
| Plain files on your disk | ✅ | ✅ | ❌ | varies |

They compose, not compete: CLAUDE.md tells Claude *how to work*, engram tells it *what has happened*, built-in compaction handles growth *within* a session.

## Documentation

| Doc | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Tile model, eviction algorithm, hook lifecycle, failure model |
| [docs/configuration.md](docs/configuration.md) | Budget tuning, store layout, hook JSON, env vars |
| [docs/faq.md](docs/faq.md) | Subscriptions vs API, CLAUDE.md comparison, data location, … |
| [SECURITY.md](SECURITY.md) | What engram touches, hardening notes, reporting |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## FAQ (short version)

- **Do I need an API key?** No — compaction runs through your local `claude` binary on your subscription.
- **Does it slow plain `claude` down?** No — the hooks exit immediately unless the session was launched via `engram`.
- **Where's my data?** `~/.engram/projects/`, plain JSON + markdown. Nothing leaves your machine.
- **Can I edit the anchor?** Yes — it's just `anchor.md`, or `engram add --anchor`.

More in [docs/faq.md](docs/faq.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Session wasn't captured | Launch with `engram`, not `claude`; restart Claude Code after installing; sessions under ~200 chars are skipped as trivial |
| No context at session start | `engram context` in the project folder — if empty, the window hasn't been seeded yet |
| "eviction deferred" message | `claude -p` couldn't run (offline?). Nothing is lost — it retries on the next capture |
| Hooks feel stale after reinstall | Open `/hooks` once inside Claude Code, or restart it |
| Wrong project's context | Stores are keyed by folder — make sure you launched from the project root |

## Roadmap

- [ ] `engram export` / `engram import` — move a window between machines
- [ ] Optional anchor refresh (`engram compact --refresh`) for pivots
- [ ] Windows support (hooks are POSIX-flavored today)
- [ ] Homebrew tap + npx installer
- [ ] Multi-agent: share one anchor across worktrees

## Uninstall

```sh
uv tool uninstall engram          # or: pipx uninstall engram
```

Then remove the two `engram hook-*` entries from `~/.claude/settings.json`
(a pre-install backup is kept at `settings.json.engram-backup`) and, if you
want the stored context gone, `rm -rf ~/.engram`.

## Development

```sh
uv sync
uv run pytest
```

The eviction and anchor logic is fully unit-tested with the token counter and compactor stubbed — no network in tests.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
