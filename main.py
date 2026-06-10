from __future__ import annotations

import argparse
import asyncio
import sys

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze medical terms from text."
    )
    parser.add_argument(
        "--cli",
        metavar="TEXT",
        help="Run analysis on the given text in the terminal (no GUI).",
    )
    args = parser.parse_args(argv)

    if args.cli:
        run_cli(args.cli)
        return 0

    from app.gui import run

    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
