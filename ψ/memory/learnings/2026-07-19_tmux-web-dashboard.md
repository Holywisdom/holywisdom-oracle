---
pattern: Building a read-only tmux web dashboard on macOS
date: 2026-07-19
tags: [tmux, ttyd, macos-sequoia, tailscale, dashboard, security]
---

# Lesson: ttyd is flaky on macOS Sequoia — roll a tiny capture-pane server

## What I tried
Requested a web dashboard to view Bo's tmux sessions. First reached for the
obvious tool: `ttyd` (terminal → web).

## What broke
`ttyd 1.7.7` + `libwebsockets 4.5.8` (homebrew, macOS Sequoia / arm64) starts,
logs `lws_create_context`, then **never prints "Listening on port" and never
opens the socket** — every client connection is refused. Not a firewall issue;
the listen socket simply isn't created. Verified with `lsof -iTCP:PORT -sTCP:LISTEN`.

## What worked
Wrote `bin/tmux-dashboard.py` — a ~120-line Python `ThreadingHTTPServer` that:
- polls `tmux capture-pane -p -t <session>` every 2s (client-side JS fetch),
- lists sessions via `tmux list-sessions -F ...`,
- is **read-only by construction**: never accepts terminal input, and only ever
  runs tmux with FIXED arg lists (no `shell=True`). The `?s=` param is validated
  against the live session list before use → injection-safe (`/pane?s=bogus` → 404).
- binds to the **Tailscale IP** (`tailscale ip -4`) so it's tailnet-private.

Python binds to the Tailscale IP fine where ttyd failed.

## Reusable takeaways
1. On a read-only "dashboard" the goal is *viewing*, not a full TTY — periodic
   `capture-pane` snapshots are simpler AND safer than a live pty bridge.
2. Confirm a server is actually listening with `lsof -iTCP:PORT -sTCP:LISTEN`,
   not just curl — curl can fail for unrelated reasons (e.g. a sandbox blocking
   network, which bit me during testing while the server was fine).
3. Bind services to the Tailscale interface/IP for private-by-default exposure.
4. Prefer fixed-arg `subprocess` + whitelist validation over string-built shell
   commands whenever request data touches a command (Rule: no secrets/no injection).

See [[oracle]] (External Brain, no secrets) · dashboard code in `bin/tmux-dashboard.*`.
