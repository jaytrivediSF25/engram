## What & why

<!-- One or two sentences: what changes, and what problem it solves. -->

## Checklist

- [ ] `uv run pytest` passes
- [ ] Behavior changes have a test
- [ ] The anchor stays sacred (nothing mutates/evicts it outside `add --anchor` / `reset`)
- [ ] No path can lose a chat — failures degrade to "stored, eviction deferred"
- [ ] Plain `claude` (without `ENGRAM_ACTIVE`) remains untouched
