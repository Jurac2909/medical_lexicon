#!/bin/sh
# Zajednicke postavke okruzenja za sve nacine rada.
# Skripta se ukljucuje (source) iz run-gui.sh, run-cli.sh i run-web.sh.

# Verzija Pythona iz snapa (core24 -> 3.12) i arhitektura (x86_64 / aarch64).
PYVER="$("$SNAP/bin/python3" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
ARCH_TRIPLET="$(uname -m)-linux-gnu"

# $SNAP je samo za citanje. Zapisivi direktorij je $SNAP_USER_COMMON za
# korisnicke naredbe, odnosno $SNAP_COMMON za daemon (koji nema korisnika).
MEDLEX_DATA_DIR="${SNAP_USER_COMMON:-$SNAP_COMMON}"
export MEDLEX_DATA_DIR
export HF_HOME="$MEDLEX_DATA_DIR/hf-cache"

# Sistemski paket python3-tk (tkinter, _tkinter.so) nije u virtualnom
# okruzenju koje gradi python plugin, pa se dodaje u putanju rucno.
export PYTHONPATH="$SNAP/app-src:$SNAP/usr/lib/python$PYVER:$SNAP/usr/lib/python$PYVER/lib-dynload${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$SNAP/usr/lib/$ARCH_TRIPLET${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TCL_LIBRARY="$SNAP/usr/share/tcltk/tcl8.6"
export TK_LIBRARY="$SNAP/usr/share/tcltk/tk8.6"

mkdir -p "$MEDLEX_DATA_DIR" "$HF_HOME"

# Rad bez interneta: model se ne pokusava provjeriti niti preuzeti, nego se
# koristi iskljucivo ono sto je vec u $HF_HOME. Ukljucuje se s:
#   sudo snap set medical-lexicon offline=true
if [ "$(snapctl get offline 2>/dev/null || true)" = "true" ]; then
  export HF_HUB_OFFLINE=1
  export TRANSFORMERS_OFFLINE=1
fi

# Pokrece aplikaciju s proslijedenim argumentima.
run_app() {
  exec "$SNAP/bin/python3" "$SNAP/app-src/main.py" "$@"
}
