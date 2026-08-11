from __future__ import annotations

import argparse
import asyncio
import os
import sys

from app import __version__
from app.fetcher import TermInfoFetcher
from app.logger import log_exceptions
from app.ner import MedicalNERAnalyzer
from app.protocols import Analyzer


@log_exceptions
def run_cli(text: str) -> None:
    analyzer: Analyzer = MedicalNERAnalyzer()
    terms = analyzer.analyze(text)
    if terms:
        asyncio.run(TermInfoFetcher().fetch_all(terms))

    if not terms:
        print("No medical terms found.")
        return

    print(f"\nFound {len(terms)} medical terms:\n")
    for t in terms:
        print(f"  - {t.text}  [{t.category}]  (confidence: {t.score:.2f})")
        if t.description:
            print(f"      {t.description}")


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    if not value.isdigit():
        return default
    return int(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze medical terms from text."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"medical-lexicon {__version__}",
    )
    parser.add_argument(
        "--cli",
        metavar="TEXT",
        help="Run analysis on the given text in the terminal (no GUI).",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help=(
            "Run the headless web service (used by the Docker image and the "
            "snap daemon on Ubuntu Core)."
        ),
    )
    parser.add_argument(
        "--host",
        metavar="ADDRESS",
        help="Address the web service binds to (env: MEDLEX_HOST).",
    )
    parser.add_argument(
        "--port",
        type=int,
        metavar="PORT",
        help="Port the web service listens on (env: MEDLEX_PORT).",
    )
    args = parser.parse_args(argv)

    if args.cli:
        run_cli(args.cli)
        return 0

    if args.web:
        from app.web import DEFAULT_HOST, DEFAULT_PORT
        from app.web import run as run_web

        host = args.host or os.environ.get("MEDLEX_HOST") or DEFAULT_HOST
        port = args.port or _env_int("MEDLEX_PORT", DEFAULT_PORT)
        run_web(host, port)
        return 0

    from app.gui import run

    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
