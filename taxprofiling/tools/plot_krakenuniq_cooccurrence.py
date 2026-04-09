#!/usr/bin/env python3
"""Plot quick summaries for KrakenUniq cooccurrence results."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def load_edges(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def add_rho_distribution(ax: plt.Axes, edges: pd.DataFrame) -> None:
    ax.hist(edges["rho"], bins=30, color="#1f77b4", alpha=0.85, edgecolor="white")
    ax.set_title("Rho Distribution")
    ax.set_xlabel("Spearman rho")
    ax.set_ylabel("Count")
    ax.axvline(0.0, color="black", linewidth=1.0, linestyle="--")


def main() -> int:
    args = parse_args()
    edges = load_edges(args.edges)
    print(f"Loaded {len(edges)} edges")
    print(f"Will write figure to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
