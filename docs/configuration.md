# Configuration

## Per-project budgets

Set at `engram init` (before first use), stored in the project's
`config.json`:

| Flag | Default | Meaning |
|---|---|---|
| `--window-tokens` | `50000` | Total window budget: anchor + sliding tiles |
| `--anchor-tokens` | `10000` | The anchor's slice — one tile of five by default |
| `--model` | `claude-opus-4-8` | Recorded for reference; compaction uses your `claude` default |

`engram add` / `engram` auto-initialize with defaults if you never run `init`.

Tuning guidance:

- **Bigger `--window-tokens`** → more recent sessions kept verbatim, more of
  each session start spent on context.
- **Bigger `--anchor-tokens`** → richer founding summary; useful for projects
  with long, decision-heavy planning phases.
- Small budgets (e.g. `--window-tokens 8000`) are great for demos — you can
  watch eviction and anchor-building happen within a few sessions.

## Store layout

```
~/.engram/projects/<sha1(project_path)[:12]>/
├── config.json     # budgets, project path, model
├── anchor.md       # pinned compacted founding context (absent until built)
├── chats/          # sliding tiles, one JSON file each, id-ordered
└── state.json      # next_id, anchor_built, anchor_tokens_actual
```

Everything is plain text — inspect, edit, or version it as you like.

## Hooks

`install.sh` registers these in `~/.claude/settings.json` (user scope):

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "\"…/engram\" hook-session-start", "timeout": 30 }] }],
    "SessionEnd":   [{ "hooks": [{ "type": "command", "command": "\"…/engram\" hook-session-end",   "timeout": 120 }] }]
  }
}
```

Both are no-ops unless `ENGRAM_ACTIVE=1` (set by the `engram` launcher).
Re-running `install.sh` is idempotent: it replaces its own entries and cleans
up any from the legacy `acw` name.

## Environment variables

| Variable | Set by | Effect |
|---|---|---|
| `ENGRAM_ACTIVE` | the `engram` launcher | Arms the hooks for that session |
