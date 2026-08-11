#!/bin/sh
# Web servis (daemon). Adresa i port citaju se iz snap konfiguracije:
#   snap set medical-lexicon port=8080
#   snap set medical-lexicon host=0.0.0.0
set -eu

. "$SNAP/bin/common.sh"

PORT="$(snapctl get port 2>/dev/null || true)"
[ -n "$PORT" ] || PORT=8080

HOST="$(snapctl get host 2>/dev/null || true)"
[ -n "$HOST" ] || HOST=0.0.0.0

run_app --web --host "$HOST" --port "$PORT"
