#!/usr/bin/env python3
"""
Plot time-series of MAG abundance across multiple samples.

Converts tab-separated abundance data into a line plot PNG with all sample dates 
visible on the X-axis. Parses sample date-time information from column names.
"""

from pathlib import Path
import re

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

input_tsv = Path("/home/jbentes/projects/bioinformatics/storage_of_results/resultados_coverm/matriz_abundancia_ria_formosa.tsv")
out_png = Path("/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/mag_abundance_timeseries_all_dates.png")
log_file = Path("/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/mag_abundance_timeseries_all_dates.log")
out_png.parent.mkdir(parents=True, exist_ok=True)

with log_file.open("a", encoding="utf-8") as log:
    def w(msg: str) -> None:
        log.write(msg + "\n")

    if not input_tsv.exists():
        w(f"ERROR missing input: {input_tsv}")
        raise SystemExit(1)

    df = pd.read_csv(input_tsv, sep="\t")
    df = df[df["Genome"] != "unmapped"].copy()
    sample_cols = [c for c in df.columns if "Relative Abundance" in c]

    def parse_sample(col: str):
        base = col.split(" Relative")[0]
        m = re.search(r"(\d{6,8})_micro_(\d)", base)
        if m:
            date = m.group(1)
            micro = int(m.group(2))
            label = f"{date}_micro{micro}"
            return (date, micro, label)
        m2 = re.search(r"(\d{6,8})", base)
        if m2:
            date = m2.group(1)
            label = date
            return (date, 9, label)
        return (base, 9, base)

    parsed = [(c, *parse_sample(c)) for c in sample_cols]
    parsed_sorted = sorted(parsed, key=lambda t: (t[1], t[2], t[0]))
    sorted_cols = [t[0] for t in parsed_sorted]
    x_labels = [t[3] for t in parsed_sorted]

    seen = {}
    x_labels_unique = []
    for lbl in x_labels:
        seen[lbl] = seen.get(lbl, 0) + 1
        if seen[lbl] == 1:
            x_labels_unique.append(lbl)
        else:
            x_labels_unique.append(f"{lbl}#{seen[lbl]}")

    x = list(range(len(sorted_cols)))

    plt.figure(figsize=(max(16, len(sorted_cols) * 0.55), 9))
    for _, row in df.iterrows():
        y = pd.to_numeric(row[sorted_cols], errors="coerce").fillna(0.0).values
        plt.plot(x, y, linewidth=1.2, alpha=0.55)

    plt.title("Abundancia dos MAGs ao longo das samples")
    plt.xlabel("Samples (todas as datas)")
    plt.ylabel("Abundancia Relativa (%)")
    plt.grid(True, linestyle="--", alpha=0.25)
    plt.xticks(x, x_labels_unique, rotation=90, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=220)
    plt.close()

    w(f"INPUT={input_tsv}")
    w(f"OUTPUT={out_png}")
    w(f"SAMPLES={len(sorted_cols)}")
    w(f"MAGS={len(df)}")

print(f"DONE\nPNG={out_png}\nLOG={log_file}\nSAMPLES={len(sorted_cols)}\nMAGS={len(df)}")
