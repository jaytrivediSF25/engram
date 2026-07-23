# Changelog

All notable changes to engram are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com); versions follow
[SemVer](https://semver.org).

## [Unreleased]

### Security
- **Secret redaction** before any tile is stored — Anthropic/OpenAI/AWS/GitHub/
  Google/Slack/Stripe keys, JWTs, PEM private keys, `NAME=secret` assignments,
  and bearer tokens are replaced with `‹redacted:KIND›`.
- **Private-by-default storage** — `~/.engram` tree created `0700`/`0600`;
  atomic writes (temp + rename); legacy stores re-hardened on load.
- **Prompt-injection fencing** for the `claude -p` compaction step — transcript
  content is fenced as untrusted data and fence markers are stripped from input.
- **Bounded transcript reads** — regular files only, 50 MB cap.
- **Atomic settings.json patch** in the installer.
- Added `docs/` threat-model-backed SECURITY.md and `tests/test_secure.py`.

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
