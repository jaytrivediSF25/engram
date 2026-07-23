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

Then, whenever you want Claude with the anchored window:

```sh
cd your-project
acw claude
```

The window loads at session start and the session is captured as the newest
tile when you quit (oldest evicts; the first eviction compacts the anchor) —
exactly like the diagram. Plain `claude` is untouched: the installed
SessionStart/SessionEnd hooks are inert unless launched via `acw claude`.

Everything runs on your Claude subscription — anchor compaction uses headless
`claude -p`, and token budgets use a built-in estimator. No API key, no
credits.

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
