#!/usr/bin/env bash
# Restart the Holywisdom bot in a FRESH GUI Terminal window, so Discord
# Keychain login works (a headless self-relaunch comes back "Not logged in").
#
# Usage:
#   bin/restart-bot.sh            # just restart (picks up already-installed skills)
#   bin/restart-bot.sh --skills   # update arra-oracle-skills first, then restart
#
# Safe to run from anywhere — including from inside the running bot. It opens a
# new Terminal.app window; the launcher there stops the old bot before starting
# the new one, so the two never run at once.
set -euo pipefail

REPO="$HOME/Code/github.com/Holywisdom/holywisdom-oracle"
LAUNCH="$REPO/bin/holywisdom-launch.sh"

if [ "${1:-}" = "--skills" ]; then
  echo "⬇️  updating arra-oracle-skills (global, claude-code)…"
  bunx --bun github:Soul-Brews-Studio/arra-oracle-skills-cli#alpha \
    install -g -y --agent claude-code
fi

if [ ! -x "$LAUNCH" ]; then
  echo "❌ launcher not found/executable: $LAUNCH" >&2
  exit 1
fi

if command -v osascript >/dev/null 2>&1; then
  echo "🪟 opening a fresh Terminal window to relaunch the bot…"
  # First run may prompt macOS for Automation permission to control Terminal — allow it.
  osascript >/dev/null <<OSA
tell application "Terminal"
  activate
  do script "clear; bash '$LAUNCH'"
end tell
OSA
  echo "✅ new bot window opening — the launcher will stop the old bot automatically."
else
  echo "⚠️  osascript not available. Run this yourself in a GUI Terminal:"
  echo "     bash '$LAUNCH'"
fi
