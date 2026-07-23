# Security Policy

## What engram touches

engram is deliberately small in surface area, but it does handle sensitive material:

- **Session transcripts.** Condensed copies of your Claude Code sessions are stored
  in plain text under `~/.engram/projects/`. They stay on your machine — engram
  makes no network calls of its own; anchor compaction goes through your local
  `claude` binary and your existing Claude subscription.
- **`~/.claude/settings.json`.** The installer patches this file to register two
  hooks. A timestamped backup is written first, and the patcher aborts on any
  malformed JSON rather than overwriting it.
- **Hooks.** The SessionStart/SessionEnd hooks are inert unless `ENGRAM_ACTIVE=1`
  is set by the `engram` launcher, and they execute only the installed `engram`
  binary — no dynamic code, no remote fetch.

## Hardening notes

- Treat `~/.engram/` like you treat shell history: if you discuss secrets in a
  session, they may end up in a stored tile. `engram reset` deletes a project's
  store; `rm -rf ~/.engram` deletes everything.
- Never commit `~/.engram/` contents to a repository.
- The compaction subprocess strips `ENGRAM_ACTIVE` from its environment so a
  headless session can never recursively capture itself.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.x (latest) | ✅ |

## Reporting a vulnerability

Please **do not** open a public issue for security reports. Use
[GitHub private vulnerability reporting](https://github.com/jaytrivediSF25/engram/security/advisories/new)
instead. You'll get an acknowledgement within a few days; fixes for confirmed
issues ship as fast as possible and are credited unless you prefer otherwise.
