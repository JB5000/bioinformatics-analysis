#!/usr/bin/env python3
"""Plot quick summaries for KrakenUniq cooccurrence results."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load_edges(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def main() -> int:
    args = parse_args()
    edges = load_edges(args.edges)
    print(f"Loaded {len(edges)} edges")
    print(f"Will write figure to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
