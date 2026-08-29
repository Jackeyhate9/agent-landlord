#!/usr/bin/env bash
# One-click script to auto-join an Agent to the Arena (Linux / macOS)
# Usage:
#   ./scripts/auto-join.sh AL-X8F2-9DK7
#   ./scripts/auto-join.sh --auto                      # fetch a fresh JOIN CODE
#   MODEL_BASE_URL=https://api.deepseek.com/v1 MODEL_API_KEY=sk-... MODEL_NAME=deepseek-chat ./scripts/auto-join.sh AL-... --adapter openai-compatible
#   CUSTOM_AGENT_URL=http://localhost:9000/act ./scripts/auto-join.sh AL-... --adapter custom-http
set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER="${ARENA_URL:-${1:-}}"
# Parse args: first non-flag is JOIN CODE, --auto flag, --server, --adapter
JOIN_CODE=""
ADAPTER="${AGENT_ADAPTER:-}"
AUTO=0
SERVER="${ARENA_URL:-https://api.thbianhua.cn}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto) AUTO=1; shift ;;
    --server) SERVER="$2"; shift 2 ;;
    --adapter) ADAPTER="$2"; shift 2 ;;
    AL-*) JOIN_CODE="$1"; shift ;;
    *) shift ;;
  esac
done

case "$(uname -s)" in
  Darwin) ASSET="arena-bridge-macos" ;;
  Linux) ASSET="arena-bridge-linux" ;;
  *) echo "Unsupported system; download Bridge from GitHub Releases" >&2; exit 1 ;;
esac
BRIDGE="$PROJ_ROOT/bridge/$ASSET"
[[ -f "$BRIDGE" ]] || BRIDGE="$PROJ_ROOT/apps/web/public/downloads/$ASSET"
if [[ ! -f "$BRIDGE" ]] && ! command -v arena-bridge >/dev/null 2>&1; then
  CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/agent-landlord"
  mkdir -p "$CACHE_DIR"
  BRIDGE="$CACHE_DIR/$ASSET"
  BASE="https://github.com/Jackeyhate9/agent-landlord/releases/latest/download"
  curl -fL "$BASE/$ASSET" -o "$BRIDGE"
  curl -fL "$BASE/$ASSET.sha256" -o "$BRIDGE.sha256"
  (cd "$CACHE_DIR" && sha256sum -c "$ASSET.sha256")
  chmod +x "$BRIDGE"
elif [[ ! -f "$BRIDGE" ]]; then
  BRIDGE="$(command -v arena-bridge)"
fi

if [[ "$AUTO" -eq 1 || -z "$JOIN_CODE" ]]; then
  if [[ -z "$JOIN_CODE" ]]; then
    echo "Fetching fresh JOIN CODE from $SERVER ..." >&2
    JOIN_CODE=$(curl -s -X POST "$SERVER/api/join-codes" -H "Content-Type: application/json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code',''))")
    [[ -n "$JOIN_CODE" ]] || { echo "Failed to fetch JOIN CODE" >&2; exit 1; }
  fi
fi

if [[ -z "$JOIN_CODE" ]]; then
  echo "JOIN CODE is required. Get one from /join or use --auto" >&2
  exit 1
fi

echo "JOIN CODE: $JOIN_CODE"
echo "Server:    $SERVER"
[[ -n "$ADAPTER" ]] && echo "Adapter:   $ADAPTER"

echo ""
echo "Starting Bridge (credentials stay on this machine) ..."
ARGS=(join "$JOIN_CODE" --server "$SERVER")
[[ -n "$ADAPTER" ]] && ARGS+=(--adapter "$ADAPTER")

exec "$BRIDGE" "${ARGS[@]}"
