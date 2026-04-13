#!/usr/bin/env python3
"""Estimate nanopore gigabases per sample date from gz FASTQ files.

This script scans a directory tree for .fastq.gz/.fq.gz files, extracts dates
from filenames, applies optional date aliases, aggregates sizes by date, and
writes CSV + HTML bar chart + log file outputs.
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DATE_TOKEN_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
DEFAULT_ALIAS = {"210805": "211220"}


@dataclass
class Record:
    path: Path
    raw_date: str
    agg_date: str
    size_bytes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate gigabases per sample date from gz FASTQ files."
    )
    parser.add_argument("--root-dir", required=True, help="Root directory to scan")
    parser.add_argument("--output-dir", required=True, help="Directory for outputs")
    parser.add_argument(
        "--compression-to-bases",
        type=float,
        default=2.0,
        help="Heuristic conversion factor: 1 compressed byte -> N estimated bases",
    )
    return parser.parse_args()


def setup_logging(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "nanopore_gbases_by_date.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
    )
    return log_path


def find_fastq_gz(root_dir: Path) -> List[Path]:
    files: List[Path] = []
    for pattern in ("*.fastq.gz", "*.fq.gz"):
        files.extend(root_dir.rglob(pattern))
    return sorted(files)


def extract_date_token(filename: str) -> Optional[str]:
    matches = DATE_TOKEN_RE.findall(filename)
    for token in matches:
        try:
            datetime.strptime(token, "%y%m%d")
            return token
        except ValueError:
            continue
    return None


def build_records(files: Iterable[Path], alias: Dict[str, str]) -> List[Record]:
    records: List[Record] = []
    skipped = 0
    for path in files:
        token = extract_date_token(path.name)
        if token is None:
            skipped += 1
            continue
        agg_date = alias.get(token, token)
        size_bytes = path.stat().st_size
        records.append(Record(path=path, raw_date=token, agg_date=agg_date, size_bytes=size_bytes))
    logging.info("Records kept: %d", len(records))
    logging.info("Skipped files without date token: %d", skipped)
    return records


def to_iso_date(yymmdd: str) -> str:
    return datetime.strptime(yymmdd, "%y%m%d").strftime("%Y-%m-%d")


def summarize(records: Iterable[Record], compression_to_bases: float) -> List[dict]:
    grouped: Dict[str, dict] = {}
    for rec in records:
        row = grouped.setdefault(
            rec.agg_date,
            {
                "agg_date": rec.agg_date,
                "display_date": to_iso_date(rec.agg_date),
                "num_files": 0,
                "size_bytes": 0,
                "source_dates": set(),
            },
        )
        row["num_files"] += 1
        row["size_bytes"] += rec.size_bytes
        row["source_dates"].add(rec.raw_date)

    summary = []
    for _, row in sorted(grouped.items(), key=lambda item: item[1]["agg_date"]):
        estimated_bases = row["size_bytes"] * compression_to_bases
        estimated_gbases = estimated_bases / 1e9
        compressed_gbytes = row["size_bytes"] / 1e9
        summary.append(
            {
                "agg_date": row["agg_date"],
                "display_date": row["display_date"],
                "num_files": row["num_files"],
                "size_bytes": row["size_bytes"],
                "compressed_gbytes": compressed_gbytes,
                "estimated_gbases": estimated_gbases,
                "source_dates": ",".join(sorted(row["source_dates"])),
            }
        )
    return summary


def write_csv(summary: List[dict], output_dir: Path) -> Path:
    csv_path = output_dir / "nanopore_gbases_by_date.csv"
    fieldnames = [
        "agg_date",
        "display_date",
        "num_files",
        "size_bytes",
        "compressed_gbytes",
        "estimated_gbases",
        "source_dates",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)
    return csv_path


def write_html_bar(summary: List[dict], output_dir: Path) -> Path:
    html_path = output_dir / "nanopore_gbases_by_date_bar.html"
    labels = [row["display_date"] for row in summary]
    values = [row["estimated_gbases"] for row in summary]

    rows = "\n".join(
        f"<tr><td>{d}</td><td>{v:.4f}</td></tr>" for d, v in zip(labels, values)
    )

    html = f"""<!DOCTYPE html>
<html lang=\"en\"> 
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Nanopore gigabases by date</title>
  <script src=\"https://cdn.plot.ly/plotly-3.4.0.min.js\"></script>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; padding: 1rem; background: #f8fafc; }}
    .box {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 0.9rem; margin-bottom: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 0.45rem; text-align: left; }}
  </style>
</head>
<body>
  <div class=\"box\">
    <h2>Nanopore bases by date</h2>
    <div id=\"chart\" style=\"height: 560px; width: 100%;\"></div>
  </div>
  <div class=\"box\">
    <h3>Estimated gigabases table</h3>
    <table>
      <thead><tr><th>Date</th><th>Estimated Gbases</th></tr></thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>
  <script>
    const x = {labels};
    const y = {values};
    const trace = {{ type: "bar", x: x, y: y, marker: {{ color: "#2563eb" }} }};
    const layout = {{
      title: "Nanopore gigabases by date",
      xaxis: {{ type: "category", tickangle: -45 }},
      yaxis: {{ title: "Estimated gigabases", tick0: 0, dtick: 5, showgrid: true }},
      bargap: 0.08,
      bargroupgap: 0.0,
      margin: {{ l: 60, r: 20, t: 60, b: 140 }}
    }};
    Plotly.newPlot("chart", [trace], layout, {{ responsive: true }});
  </script>
</body>
</html>
"""

    html_path.write_text(html, encoding="utf-8")
    return html_path


def main() -> None:
    args = parse_args()
    root_dir = Path(args.root_dir)
    output_dir = Path(args.output_dir)
    setup_logging(output_dir)

    logging.info("Root directory: %s", root_dir)
    logging.info("Output directory: %s", output_dir)
    logging.info("Aggregation alias: %s", DEFAULT_ALIAS)
    logging.info("Heuristic: 1 compressed byte -> %.2f estimated bases", args.compression_to_bases)

    files = find_fastq_gz(root_dir)
    logging.info("Discovered %d gz FASTQ files", len(files))

    records = build_records(files, DEFAULT_ALIAS)
    if not records:
        logging.error("No dated FASTQ files found under %s", root_dir)
        raise SystemExit(1)

    summary = summarize(records, args.compression_to_bases)
    csv_path = write_csv(summary, output_dir)
    html_path = write_html_bar(summary, output_dir)

    total_gbases = sum(row["estimated_gbases"] for row in summary)
    logging.info("Wrote summary CSV: %s", csv_path)
    logging.info("Wrote plot HTML: %s", html_path)
    logging.info("Total estimated gigabases across all dates: %.4f", total_gbases)


if __name__ == "__main__":
    main()
