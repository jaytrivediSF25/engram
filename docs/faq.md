# FAQ

### Does this need an API key or credits?

No. Everything runs on your existing Claude subscription. Anchor compaction
shells out to headless `claude -p`; token budgets use a local estimator.

### Does it change how plain `claude` behaves?

No. The hooks installed in `~/.claude/settings.json` return immediately unless
the session was launched via the `engram` command (which sets `ENGRAM_ACTIVE=1`).

### How is this different from Claude Code's built-in compaction?

Built-in compaction manages context *within* one session. engram manages
context *across* sessions — yesterday's session, last week's planning chat.
They compose: engram feeds the window in at session start; Claude's own
compaction still handles in-session growth.

### How is this different from CLAUDE.md?

CLAUDE.md is hand-written, static instructions. engram is automatic, evolving
memory: sessions are captured as they happen, and the founding ones are
compacted into the anchor without you writing anything. Use both — CLAUDE.md
for *how to work*, engram for *what has happened*.

### Where is my data?

`~/.engram/projects/<hash>/` — plain JSON and markdown on your disk. Nothing
leaves your machine except the compaction prompt, which goes through your own
`claude` binary like any other session.

### Can I edit the anchor by hand?

Yes. It's just `anchor.md` in the project's store — edit it, or replace it
wholesale with `engram add --anchor --file notes.md`.

### What happens if I discuss secrets in a session?

They may be captured into a tile, like shell history. See
[SECURITY.md](../SECURITY.md). `engram reset` wipes a project's store.

### Why did my session not get captured?

Sessions under ~200 characters of condensed conversation are skipped as
trivial. Also check that you launched with `engram`, not plain `claude`, and
that you restarted Claude Code after installing.

### Can I use different budgets per project?

Yes: `engram init --window-tokens N --anchor-tokens M` before first use
(defaults: 50,000 / 10,000).
