from __future__ import annotations

import os
import tempfile
from pathlib import Path

ENV_DATA_DIR = "MEDLEX_DATA_DIR"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_ENV_CANDIDATES = (
    ENV_DATA_DIR,
    "SNAP_USER_COMMON",
    "SNAP_COMMON",
)


def _configured_base() -> Path:
    """Return the configured base directory, without creating it.

    Priority: MEDLEX_DATA_DIR (Docker, manual override), then the writable
    directories a snap provides, then the project directory (development).
    """
    for name in _ENV_CANDIDATES:
        value = os.environ.get(name)
        if value:
            return Path(value)
    return PROJECT_ROOT


def _ensure_writable(path: Path) -> Path:
    """Create the directory, falling back to a temp directory if read-only.

    Inside a snap the code lives in a read-only $SNAP, and a container may run
    with a read-only root filesystem, so a failure here must not abort the app.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "medical-lexicon"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def data_dir() -> Path:
    """Writable directory for the log file, exports and the model cache."""
    return _ensure_writable(_configured_base())


def export_dir() -> Path:
    """Directory where the web service writes CSV and PDF exports."""
    return _ensure_writable(data_dir() / "exports")


def model_cache_dir() -> Path:
    """Directory used by transformers as its download cache.

    Set as HF_HOME by the launcher scripts so the model is downloaded once and
    kept across restarts (in a snap, in $SNAP_COMMON rather than read-only
    $SNAP).
    """
    configured = os.environ.get("HF_HOME")
    if configured:
        return _ensure_writable(Path(configured))
    return _ensure_writable(data_dir() / "hf-cache")
