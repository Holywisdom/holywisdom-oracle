#!/usr/bin/env bash
# Canonical launcher for the Holywisdom Discord bot.
# Stops any running Holywisdom bot, then execs a fresh one so newly
# installed skills are picked up.
#
# MUST run inside a GUI Terminal (Terminal.app) — Discord login needs
# Keychain, which is unavailable over SSH-only / tmux-only sessions.
set -euo pipefail

REPO="$HOME/Code/github.com/Holywisdom/holywisdom-oracle"
export DISCORD_STATE_DIR="$HOME/.claude/channels/discord-holywisdom"

# Stop any running Holywisdom bot. macOS `pgrep -f` truncates/misses long
# cmdlines, so match on full args via `ps`. Capture ps output FIRST so the
# awk in the pipeline can't match its own command line. The --name/--channels
# signature means other/unrelated `claude` sessions are never touched.
SELF="$$"
PSOUT="$(ps -Ao pid=,command=)"
OLD="$(printf '%s\n' "$PSOUT" \
  | awk -v self="$SELF" '/--name Holywisdom --channels plugin:discord/ && $1 != self {print $1}')"
if [ -n "${OLD}" ]; then
  echo "⏹  stopping old Holywisdom bot (pids: $(echo ${OLD} | tr '\n' ' '))"
  # shellcheck disable=SC2086
  kill ${OLD} 2>/dev/null || true
  sleep 2   # let the Discord gateway disconnect before reconnecting
fi

cd "$REPO"
echo "🔮 launching Holywisdom bot…"
exec claude --dangerously-skip-permissions \
  --name Holywisdom \
  --channels plugin:discord@claude-plugins-official
