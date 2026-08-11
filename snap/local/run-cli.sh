#!/bin/sh
# Analiza teksta u terminalu:
#   medical-lexicon.cli "The patient has pneumonia."
set -eu

. "$SNAP/bin/common.sh"

case "${1:-}" in
  "")
    echo "Uporaba: $SNAP_INSTANCE_NAME.cli \"tekst za analizu\"" >&2
    echo "         $SNAP_INSTANCE_NAME.cli --help" >&2
    exit 2
    ;;
  -*)
    # Zastavice (--help, --version, --web ...) prosljeduju se izravno.
    run_app "$@"
    ;;
  *)
    # Sve ostalo je tekst za analizu, spojen u jedan argument.
    run_app --cli "$*"
    ;;
esac
