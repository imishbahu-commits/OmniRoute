#!/usr/bin/env bash
# Start OmniRoute in a Codespace, make the port public, disable the login, and
# print the URL to open on a phone. Safe to re-run: it reuses a running server.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

PORT="${PORT:-20128}"
LOG="/tmp/omniroute.log"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }

# ── 1. Start the server if it isn't already up ──────────────────────────────
if curl -sS -m 5 -o /dev/null "http://127.0.0.1:${PORT}/v1/models" 2>/dev/null; then
  bold "✓ OmniRoute is already running."
else
  bold "▶ Starting OmniRoute (first boot compiles for a few minutes)..."
  # Call the dev runner directly rather than `npm run dev`: that script hardcodes
  # --max-old-space-size=8192, which is the whole machine on a 2-core/8gb
  # codespace and gets the process OOM-killed mid-compile. 5 GB leaves headroom.
  HOST=0.0.0.0 nohup node --max-old-space-size=5120 scripts/dev/run-next.mjs dev >"$LOG" 2>&1 &
fi

# ── 2. Make the forwarded port public (Codespaces only) ─────────────────────
# Do this early so the port is public by the time the server answers. The port
# must already be forwarded for `gh` to accept it, so retry while it boots.
if [ -n "${CODESPACE_NAME:-}" ]; then
  if ! command -v gh >/dev/null 2>&1; then
    bold "⚠ GitHub CLI (gh) not found — cannot set port visibility automatically."
    bold "  Use the Ports tab: long-press ${PORT} > Port Visibility > Public."
  else
    bold "▶ Making port ${PORT} public..."
    PUBLIC_OK=0
    for _ in $(seq 1 12); do
      if gh codespace ports visibility "${PORT}:public" -c "$CODESPACE_NAME" >/dev/null 2>&1; then
        bold "✓ Port ${PORT} is public — anyone with the link can reach it."
        PUBLIC_OK=1
        break
      fi
      sleep 5
    done
    if [ "$PUBLIC_OK" -eq 0 ]; then
      bold "⚠ Could not set port ${PORT} public automatically."
      bold "  Do it by hand: Ports tab > long-press ${PORT} > Port Visibility > Public."
    fi
  fi
fi

# ── 3. Wait for boot, then switch off the dashboard login ───────────────────
node scripts/dev/setup-public-mode.mjs --timeout 600 || {
  bold "⚠ Could not disable the login automatically."
  bold "  Check the log:  tail -50 ${LOG}"
}

# ── 4. Print the link ───────────────────────────────────────────────────────
if [ -n "${CODESPACE_NAME:-}" ]; then
  URL="https://${CODESPACE_NAME}-${PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  node scripts/dev/mobile-url.mjs --url "$URL" || {
    echo ""
    bold "📱 Open this on your phone:"
    echo "   ${URL}/dashboard"
  }
else
  node scripts/dev/mobile-url.mjs || true
fi
