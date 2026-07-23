# Changelog

All notable changes to engram are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com); versions follow
[SemVer](https://semver.org).

## [0.1.0] — 2026-07-23

Initial release.

### Added
- **Anchored sliding window**: token-budgeted tiles per project — a pinned
  anchor of compacted founding context plus a sliding window of recent
  sessions at full fidelity.
- `engram` launcher: bare command opens Claude Code with the window injected
  at SessionStart and the session captured at SessionEnd; extra flags pass
  through to `claude`.
- Anchor compaction via headless `claude -p` — runs on the Claude
  subscription, no API key or credits.
- `install.sh`: installs the CLI (uv/pipx/pip) and idempotently patches
  `~/.claude/settings.json` hooks, with backup and legacy-entry cleanup.
- CLI surface: `init`, `add` (incl. `--anchor`), `context` (incl. `--json`),
  `status`, `reset`.
- Safety guarantees: compaction failure defers eviction (never loses a chat);
  hooks are inert without `ENGRAM_ACTIVE`; newest chat is never evicted.

[0.1.0]: https://github.com/jaytrivediSF25/engram/releases/tag/v0.1.0
