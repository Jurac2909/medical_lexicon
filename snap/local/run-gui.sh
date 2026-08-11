#!/bin/sh
# Graficko sucelje (Tkinter). Zahtijeva X11 ili Wayland sjednicu.
set -eu

. "$SNAP/bin/common.sh"

run_app "$@"
