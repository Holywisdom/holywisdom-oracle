#!/usr/bin/env bash
# Manage the read-only tmux web dashboard (private over Tailscale).
#
#   bin/tmux-dashboard.sh start [port]   # start (default port 7681, Tailscale IP)
#   bin/tmux-dashboard.sh stop
#   bin/tmux-dashboard.sh status
#   bin/tmux-dashboard.sh restart [port]
set -euo pipefail

REPO="$HOME/Code/github.com/Holywisdom/holywisdom-oracle"
PY="$REPO/bin/tmux-dashboard.py"
STATE="$HOME/.claude/channels/discord-holywisdom"
PIDFILE="$STATE/tmux-dashboard.pid"
LOG="$STATE/tmux-dashboard.log"
PORT="${2:-7681}"
HOST="$(tailscale ip -4 2>/dev/null | head -1 || echo 127.0.0.1)"

running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

start() {
  if running; then echo "already running (pid $(cat "$PIDFILE")) — http://${HOST}:${PORT}"; return 0; fi
  mkdir -p "$STATE"
  nohup python3 "$PY" --host "$HOST" --port "$PORT" >"$LOG" 2>&1 &
  echo $! > "$PIDFILE"
  # confirm it came up
  for _ in $(seq 1 20); do
    if curl -s -o /dev/null -m2 "http://${HOST}:${PORT}/"; then
      echo "✅ tmux dashboard: http://${HOST}:${PORT}  (read-only, Tailscale-only)"; return 0
    fi
    sleep 0.3   # give python a moment to bind before retrying
  done
  echo "⚠️ started (pid $(cat "$PIDFILE")) but no HTTP response yet — check $LOG"; tail -5 "$LOG" 2>/dev/null || true
}

stop() {
  if running; then kill "$(cat "$PIDFILE")" 2>/dev/null || true; fi
  # sweep any stray instance too
  pkill -f "tmux-dashboard.py" 2>/dev/null || true
  rm -f "$PIDFILE"
  echo "⏹ stopped"
}

status() {
  if running; then echo "running (pid $(cat "$PIDFILE")) — http://${HOST}:${PORT}";
  else echo "not running"; fi
}

case "${1:-start}" in
  start)   start ;;
  stop)    stop ;;
  status)  status ;;
  restart) stop; start ;;
  *) echo "usage: $0 {start [port]|stop|status|restart [port]}"; exit 1 ;;
esac
