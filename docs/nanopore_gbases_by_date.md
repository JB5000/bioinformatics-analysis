# Nanopore Gigabases By Date

This utility estimates nanopore gigabases per sampling date using compressed
FASTQ file sizes (`.fastq.gz` / `.fq.gz`).

## Script

`common/scripts/nanopore_gbases_by_date.py`

## What It Does

- Scans a root directory recursively for gz FASTQ files.
- Extracts `YYMMDD` date tokens from file names.
- Applies alias mapping `210805 -> 211220` for aggregation.
- Computes estimated gigabases from compressed bytes (default factor: `2.0`).
- Writes outputs to the selected output directory:
  - `nanopore_gbases_by_date.csv`
  - `nanopore_gbases_by_date_bar.html`
  - `nanopore_gbases_by_date.log`

## Example

```bash
python3 common/scripts/nanopore_gbases_by_date.py \
  --root-dir /path/to/nanopore_fastq_tree \
  --output-dir /path/to/output
```

## Notes

- The gigabase values are heuristic estimates, not basecalled exact counts.
- Files without a valid six-digit date token are logged and skipped.