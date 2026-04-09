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

## Matrix Orientation
If your KrakenUniq export has taxa in rows and samples in columns, transpose first:

```bash
python - <<'PY'
import pandas as pd
m = pd.read_csv('krakenuniq_krakenuniq_standard.tsv', sep='\t').set_index('taxonomy_id').T
m.index.name = 'sample_id'
m.to_csv('krakenuniq_krakenuniq_standard.transposed.tsv', sep='\t')
PY
```

## Output Files
- `cooccurrence_edges.csv`: pairwise taxa correlations with p/q values.
- `cooccurrence_nodes.csv`: node-level metrics.
- `cooccurrence_network.gexf`: graph for Gephi/Cytoscape.
- `ratio_matrix.csv`: log-ratios among top taxa.
- `summary.json`: high-level run metadata.
