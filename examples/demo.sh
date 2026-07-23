#!/usr/bin/env bash
# Watch the anchored sliding window work in miniature — tiny budgets so
# eviction and anchor-building happen in seconds instead of weeks.
#
# Usage: ./examples/demo.sh   (needs engram installed + Claude Code logged in)
set -euo pipefail

DEMO=$(mktemp -d /tmp/engram-demo.XXXXXX)
cd "$DEMO"
echo "demo project: $DEMO"

engram init --window-tokens 800 --anchor-tokens 250

session() { # simulate a captured session
  engram add --text "$1" >/dev/null
}

echo "→ session 1 (founding: the plan)"
session "$(printf 'Planning session: building shoplite, an inventory tracker for small retail. Constraints: offline-first on Raspberry Pi, SQLite only, \$2k budget, Q3 deadline. Decision: Python+Flask over Node. Owner requires existing USB barcode scanners to work.%.0s ' 1 2 3)"

echo "→ session 2 (feature work)"
session "$(printf 'Session 2: built product table and stock endpoints. Fixed SQLite locking under concurrent scans with WAL mode.%.0s ' 1 2 3 4)"

echo "→ session 3 (more feature work — this overflows the window)"
session "$(printf 'Session 3: barcode scanner integration. HID events parsed, debounced double-scans, works at the register.%.0s ' 1 2 3 4)"

echo
echo "The founding session was evicted and compacted into the pinned anchor:"
echo "────────────────────────────────────────────────────────────"
engram status
echo "────────────────────────────────────────────────────────────"
engram context | head -30
echo
echo "Clean up with:  cd $DEMO && engram reset --force"
