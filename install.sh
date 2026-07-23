#!/usr/bin/env bash
# engram quickstart installer:
#   1. installs the `engram` CLI
#   2. patches ~/.claude/settings.json with SessionStart/SessionEnd hooks so every
#      Claude Code session auto-loads and auto-saves the anchored sliding window
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Installing engram CLI"
if command -v uv >/dev/null 2>&1; then
  uv tool install --force --editable . >/dev/null
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force . >/dev/null
else
  python3 -m pip install --user . >/dev/null
fi

ENGRAM="$HOME/.local/bin/engram"
if [ ! -x "$ENGRAM" ]; then
  ENGRAM="$(command -v engram || true)"
fi
if [ -z "$ENGRAM" ]; then
  echo "error: engram did not land on PATH (expected ~/.local/bin/engram)" >&2
  exit 1
fi
echo "    installed: $ENGRAM ($("$ENGRAM" --version))"

echo "==> Patching ~/.claude/settings.json (backup kept as settings.json.engram-backup)"
ENGRAM_BIN="$ENGRAM" python3 - <<'PY'
import json, os, shutil

path = os.path.expanduser("~/.claude/settings.json")
engram = os.environ["ENGRAM_BIN"]
settings = {}
if os.path.exists(path):
    with open(path) as f:
        settings = json.load(f)  # malformed file -> abort before touching anything
    shutil.copy2(path, path + ".engram-backup")
else:
    os.makedirs(os.path.dirname(path), exist_ok=True)

hooks = settings.setdefault("hooks", {})

def is_ours(h, name):
    # commands look like: "/path/to/<name>" hook-session-start (note the quotes)
    return f"{name} hook-" in h.get("command", "").replace('"', "")

# Purge our hooks (and any from the legacy `acw` name) so re-installs never duplicate.
for event in ("SessionStart", "SessionEnd"):
    for entry in hooks.get(event, []):
        entry["hooks"] = [
            h for h in entry.get("hooks", [])
            if not (is_ours(h, "engram") or is_ours(h, "acw"))
        ]
    hooks[event] = [e for e in hooks.get(event, []) if e.get("hooks")]

def ensure(event, cmd, timeout):
    hooks.setdefault(event, []).append(
        {"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]}
    )
    return "added"

r1 = ensure("SessionStart", f'"{engram}" hook-session-start', 30)
r2 = ensure("SessionEnd", f'"{engram}" hook-session-end', 120)

with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
print(f"    SessionStart hook {r1}, SessionEnd hook {r2}")
PY

cat <<'EOF'

✔ engram installed

Quickstart:
  cd your-project
  engram            # Claude with the anchored window: loads at start, saves at exit
  claude                # plain Claude, engram stays out of the way

Inspect the window any time:
  engram status            # tiles + token budgets
  engram context           # the anchor + recent chats

Runs entirely on your Claude subscription (via headless `claude -p`) —
no API key or credits needed.

If Claude Code is already running, restart it (or open /hooks once) to load the hooks.
EOF
