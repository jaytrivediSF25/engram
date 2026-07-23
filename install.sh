#!/usr/bin/env bash
# acw quickstart installer:
#   1. installs the `acw` CLI
#   2. patches ~/.claude/settings.json with SessionStart/SessionEnd hooks so every
#      Claude Code session auto-loads and auto-saves the anchored sliding window
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Installing acw CLI"
if command -v uv >/dev/null 2>&1; then
  uv tool install --force --editable . >/dev/null
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force . >/dev/null
else
  python3 -m pip install --user . >/dev/null
fi

ACW="$HOME/.local/bin/acw"
if [ ! -x "$ACW" ]; then
  ACW="$(command -v acw || true)"
fi
if [ -z "$ACW" ]; then
  echo "error: acw did not land on PATH (expected ~/.local/bin/acw)" >&2
  exit 1
fi
echo "    installed: $ACW ($("$ACW" --version))"

echo "==> Patching ~/.claude/settings.json (backup kept as settings.json.acw-backup)"
ACW_BIN="$ACW" python3 - <<'PY'
import json, os, shutil

path = os.path.expanduser("~/.claude/settings.json")
acw = os.environ["ACW_BIN"]
settings = {}
if os.path.exists(path):
    with open(path) as f:
        settings = json.load(f)  # malformed file -> abort before touching anything
    shutil.copy2(path, path + ".acw-backup")
else:
    os.makedirs(os.path.dirname(path), exist_ok=True)

hooks = settings.setdefault("hooks", {})

def ensure(event, cmd, timeout):
    entries = hooks.setdefault(event, [])
    for entry in entries:                      # merge: update our hook if present
        for h in entry.get("hooks", []):
            if "acw hook-" in h.get("command", ""):
                h.update({"type": "command", "command": cmd, "timeout": timeout})
                return "updated"
    entries.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    return "added"

r1 = ensure("SessionStart", f'"{acw}" hook-session-start', 30)
r2 = ensure("SessionEnd", f'"{acw}" hook-session-end', 120)

with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
print(f"    SessionStart hook {r1}, SessionEnd hook {r2}")
PY

cat <<'EOF'

✔ acw installed

Quickstart:
  cd your-project
  claude                # context auto-loads at start, session auto-saves at exit
  # or: acw claude      # same, with context injected as the opening message

Inspect the window any time:
  acw status            # tiles + token budgets
  acw context           # the anchor + recent chats

Note: anchor compaction + exact token counts use the Anthropic API
(ANTHROPIC_API_KEY or `ant auth login`). Without it, chats are still
captured using estimated token counts.

If Claude Code is already running, restart it (or open /hooks once) to load the hooks.
EOF
