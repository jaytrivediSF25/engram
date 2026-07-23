# acw — anchored sliding window context manager

A CLI implementing an **anchored sliding window** for AI-agent context:

- The context window is divided into token-budgeted tiles.
- Tile 0 is a **pinned anchor**: an LLM-compacted summary of the project's
  *founding* context (goals, constraints, original decisions). It is written
  once — at the first eviction — and never evicted.
- The rest is a **sliding window** of recent chats at full fidelity. As new
  chats arrive, the oldest tile drops off.

This combines what each pure approach does well: a plain sliding window keeps
recent turns verbatim but forgets why the project exists; full compaction
remembers everything but flattens recent detail. The anchor costs one tile of
budget and keeps the founding context forever.

## Quickstart

```sh
git clone <this-repo> acw
cd acw
./install.sh
```

The installer puts `acw` on your PATH and patches `~/.claude/settings.json`
(backup kept) with two hooks:

- **SessionStart** — injects the project's anchor + recent chats into every
  new Claude Code session automatically
- **SessionEnd** — captures the session transcript as the newest sliding tile
  when you quit, evicting the oldest tile (and compacting the anchor the first
  time) as needed

So after installing, just run `claude` in any project — the window loads at
start and updates at exit, exactly like the diagram. Restart Claude Code (or
open `/hooks` once) if it was already running.

Anchor compaction and exact token counts use the Anthropic API
(`ANTHROPIC_API_KEY` or an `ant auth login` profile). Without it, chats are
still captured using estimated token counts.

## Usage

```sh
acw init --window-tokens 50000 --anchor-tokens 10000   # optional; add auto-inits
acw add < transcript.md          # store a chat (also --text / --file)
acw add --anchor --text "..."    # force content into the pinned anchor slot
acw context                      # print anchor + recent chats (--json available)
acw claude                       # launch Claude Code with the context preloaded
acw status                       # tiles, token counts, budget usage
acw reset                        # delete this project's store
```

Stores are keyed by the current working directory, under `~/.acw/projects/`.

## Using from Claude Code / Codex

Add to the project's `CLAUDE.md` or `AGENTS.md`:

> At the start of a session, run `acw context` and treat its output as prior
> project context. After completing significant work, pipe a concise transcript
> of the exchange to `acw add`.

## Development

```sh
uv sync
uv run pytest
```
