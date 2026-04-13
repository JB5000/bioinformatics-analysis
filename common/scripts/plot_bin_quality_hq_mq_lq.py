#!/usr/bin/env python3
"""
Generate a single Completeness vs Contamination plot for all bins,
colored by quality class: HQ, MQ, and LQ.

Output files are created next to the input TSV by default:
- bin_summary_all_bins_HQ_MQ_LQ_colored.png
- bin_summary_all_bins_HQ_MQ_LQ_colored.log
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot all bins with HQ/MQ/LQ colors (x=Completeness, y=Contamination)."
    )
    parser.add_argument(
        "--input-tsv",
        required=True,
        help="Path to bin_summary.tsv (or equivalent table with bin/completeness/contamination columns).",
    )
    parser.add_argument(
        "--output-png",
        default="",
        help="Optional output PNG path. Default: <input_dir>/bin_summary_all_bins_HQ_MQ_LQ_colored.png",
    )
    parser.add_argument(
        "--log-file",
        default="",
        help="Optional log path. Default: <input_dir>/bin_summary_all_bins_HQ_MQ_LQ_colored.log",
    )
    return parser.parse_args()


def _pick_column(columns_lower: dict[str, str], *candidates: str) -> str | None:
    for candidate in candidates:
        if candidate in columns_lower:
            return columns_lower[candidate]
    return None


def main() -> int:
    args = parse_args()

    input_tsv = Path(args.input_tsv).expanduser().resolve()
    out_dir = input_tsv.parent
    output_png = Path(args.output_png).expanduser().resolve() if args.output_png else out_dir / "bin_summary_all_bins_HQ_MQ_LQ_colored.png"
    log_file = Path(args.log_file).expanduser().resolve() if args.log_file else out_dir / "bin_summary_all_bins_HQ_MQ_LQ_colored.log"

    output_png.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with log_file.open("a", encoding="utf-8") as log:
        def w(msg: str) -> None:
            log.write(f"{datetime.now().isoformat()} | {msg}\n")

        w(f"Input TSV: {input_tsv}")

        if not input_tsv.exists():
            w("ERROR: input TSV does not exist")
            return 1

        df = pd.read_csv(input_tsv, sep="\t")
        cols_lower = {c.lower().strip(): c for c in df.columns}

        bin_col = _pick_column(cols_lower, "bin", "id") or list(df.columns)[0]
        comp_col = _pick_column(cols_lower, "completeness", "completeness_checkm2")
        cont_col = _pick_column(cols_lower, "contamination", "contamination_checkm2")

        if comp_col is None or cont_col is None:
            w(f"ERROR: missing completeness/contamination columns; found: {list(df.columns)}")
            return 1

        clean = df[[bin_col, comp_col, cont_col]].copy()
        clean = clean.rename(
            columns={bin_col: "bin", comp_col: "completeness", cont_col: "contamination"}
        )
        clean["completeness"] = pd.to_numeric(clean["completeness"], errors="coerce")
        clean["contamination"] = pd.to_numeric(clean["contamination"], errors="coerce")
        clean = clean.dropna(subset=["completeness", "contamination"]).copy()

        if clean.empty:
            w("ERROR: no numeric rows after cleaning")
            return 1

        hq = clean[(clean["completeness"] >= 90) & (clean["contamination"] <= 5)]
        mq = clean[
            (clean["completeness"] >= 50)
            & (clean["contamination"] <= 10)
            & ~((clean["completeness"] >= 90) & (clean["contamination"] <= 5))
        ]
        lq = clean.drop(hq.index.union(mq.index))

        w(
            "Rows plotted total: "
            f"{len(clean)} | HQ: {len(hq)} | MQ: {len(mq)} | LQ: {len(lq)}"
        )

        plt.figure(figsize=(10.5, 7.5))
        plt.scatter(
            lq["completeness"],
            lq["contamination"],
            s=22,
            alpha=0.65,
            c="#ef4444",
            edgecolors="none",
            label=f"LQ (n={len(lq)})",
        )
        plt.scatter(
            mq["completeness"],
            mq["contamination"],
            s=24,
            alpha=0.75,
            c="#f59e0b",
            edgecolors="none",
            label=f"MQ (n={len(mq)})",
        )
        plt.scatter(
            hq["completeness"],
            hq["contamination"],
            s=28,
            alpha=0.85,
            c="#22c55e",
            edgecolors="black",
            linewidths=0.2,
            label=f"HQ (n={len(hq)})",
        )

        plt.axvline(90, linestyle="--", linewidth=1.2, color="#16a34a", alpha=0.8)
        plt.axvline(50, linestyle="--", linewidth=1.0, color="#f59e0b", alpha=0.6)
        plt.axhline(5, linestyle="--", linewidth=1.2, color="#dc2626", alpha=0.8)
        plt.axhline(10, linestyle="--", linewidth=1.0, color="#f59e0b", alpha=0.6)

        plt.xlabel("Completeness (%)")
        plt.ylabel("Contamination (%)")
        plt.title("All bins by quality class: HQ / MQ / LQ")
        plt.xlim(0, 100)
        plt.ylim(bottom=0)
        plt.grid(True, linestyle="--", alpha=0.28)
        plt.legend(loc="upper right", frameon=True)
        plt.tight_layout()
        plt.savefig(output_png, dpi=230)
        plt.close()

        w(f"PNG written: {output_png}")

    print(f"DONE\nPNG={output_png}\nLOG={log_file}\nROWS={len(clean)}\nHQ={len(hq)}\nMQ={len(mq)}\nLQ={len(lq)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
