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


def add_top_associations(ax: plt.Axes, edges: pd.DataFrame, top_n: int = 8) -> None:
    significant = edges[edges["q_value"] <= 0.05].copy()
    if significant.empty:
        ax.set_title("Top Associations")
        ax.text(0.5, 0.5, "No significant edges", ha="center", va="center")
        ax.axis("off")
        return

    top_pos = significant.nlargest(top_n // 2, "rho")
    top_neg = significant.nsmallest(top_n // 2, "rho")
    combined = pd.concat([top_neg, top_pos], axis=0)
    labels = [f"{l}|{r}" for l, r in zip(combined["taxon_left"], combined["taxon_right"])]
    colors = ["#d62728" if value < 0 else "#2ca02c" for value in combined["rho"]]
    ax.barh(labels, combined["rho"], color=colors, alpha=0.9)
    ax.set_title("Top Positive/Negative Associations")
    ax.set_xlabel("Spearman rho")


def main() -> int:
    args = parse_args()
    edges = load_edges(args.edges)
    figure, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    add_rho_distribution(axes[0], edges)
    add_top_associations(axes[1], edges, top_n=10)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)
    plt.close(figure)
    print(f"Loaded {len(edges)} edges")
    print(f"Saved plot to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
