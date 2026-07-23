# Security Policy

engram stores condensed copies of your Claude Code sessions on disk and replays
them into future sessions. That means it handles potentially sensitive material,
and it runs code paths triggered by session content. This document is the threat
model and the controls that back it — the controls are implemented and tested,
not aspirational.

## Design principles

1. **Stay local.** engram makes no network calls of its own. Anchor compaction
   runs through your local `claude` binary on your existing subscription. No API
   key, no telemetry, no third-party endpoint.
2. **Least exposure on disk.** The store is private to your user account and
   secrets are scrubbed before anything is written.
3. **Never lose data, never corrupt config.** Every write is atomic; every
   failure degrades safely.
4. **Treat session content as untrusted data,** including in the one place it is
   fed to a model.

## Threat model & controls

| Threat | Control | Where |
|---|---|---|
| A local secret (API key, token, private key) typed into a session gets persisted and replayed into every future session | **Secret redaction** — credential-shaped strings (Anthropic/OpenAI/AWS/GitHub/Google/Slack/Stripe keys, JWTs, PEM private-key blocks, `NAME=secret` assignments, bearer tokens) are replaced with `‹redacted:KIND›` markers *before* a tile is stored | `secure.py` → `redact`, applied in `store.add_chat` and `add --anchor`; tested in `tests/test_secure.py` |
| Another user (or a compromised process under a different UID) reads your captured project detail | **Private-by-default storage** — `~/.engram` and everything under it is created `0700`/`0600`; loads re-tighten legacy stores | `secure.py` → `harden_path` / `secure_write_text` |
| A malicious/booby-trapped session transcript injects instructions into the autonomous compaction step (`claude -p`) | **Prompt-injection fencing** — transcript content is enclosed in explicit `BEGIN/END UNTRUSTED TRANSCRIPT` markers, the system prompt forbids acting on anything inside them, and our own fence markers are stripped from the content so they can't be spoofed | `compact.py` |
| A huge or special file (fifo/device) supplied as the transcript path OOMs or hangs the hook | **Bounded, type-checked reads** — only regular files are read, capped at 50 MB | `capture.py` → `condense_transcript` |
| Command injection via session content or file paths | **No shell, ever** — subprocess is invoked in list form (`["claude", "-p", prompt]`); there is no `shell=True`, `os.system`, or `eval` anywhere in the codebase | `compact.py`, verified by grep in CI review |
| An interrupted install corrupts `~/.claude/settings.json` and breaks Claude Code | **Atomic patch + backup + abort-on-malformed** — the installer refuses to run against unparseable JSON, writes a timestamped backup, and renames the new file into place atomically | `install.sh` |
| The headless compaction session recursively captures itself as a chat | **Env isolation** — `ENGRAM_ACTIVE` is stripped from the compaction subprocess's environment so its own SessionEnd hook is inert | `compact.py` → `_run_claude` |

## Residual risks (know these)

- **Redaction is best-effort.** It catches common credential *shapes*; a secret
  with no recognizable structure (a plain passphrase in prose) can still be
  captured. Treat `~/.engram` as sensitive regardless — it's like shell history.
- **The anchor and tiles are plaintext.** They're private to your user, not
  encrypted at rest. Full-disk encryption (FileVault, LUKS) covers the rest.
- **Compaction fencing mitigates but cannot fully eliminate prompt injection.**
  It runs on your own machine over your own sessions; the blast radius is a
  poorly-summarized anchor, which you can inspect (`engram context`) and rewrite
  (`engram add --anchor`).

## Wiping data

```sh
engram reset          # this project's store
rm -rf ~/.engram      # everything
```

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.x (latest) | ✅ |

## Reporting a vulnerability

Please **do not** open a public issue for security reports. Use
[GitHub private vulnerability reporting](https://github.com/jaytrivediSF25/engram/security/advisories/new).
You'll get an acknowledgement within a few days; confirmed issues are fixed as
fast as possible and credited unless you prefer otherwise.
