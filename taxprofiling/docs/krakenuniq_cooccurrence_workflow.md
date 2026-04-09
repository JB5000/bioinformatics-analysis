# KrakenUniq Cooccurrence Workflow

## Goal
Run a taxonomy-only cooccurrence analysis from KrakenUniq abundance tables and generate network-ready outputs.

## Required Inputs
- KrakenUniq table in TSV format.
- A table with samples in rows and taxa in columns.
- Python environment with pandas, scipy, statsmodels, networkx.

## Run Commands
```bash
python taxprofiling/tools/analyze_cooccurrence_and_ratios.py \
  --abundance-table path/to/krakenuniq_table.tsv \
  --output-dir taxprofiling/results/krakenuniq_taxonomy_only \
  --sample-column sample_id \
  --max-taxa 40 \
  --ratio-taxa 15
```
