#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IN_TSV="${ROOT}/../_tmp_krakenuniq_redo/krakenuniq_krakenuniq_standard.tsv"
TRANSPOSED="${ROOT}/../_tmp_krakenuniq_redo/krakenuniq_krakenuniq_standard.transposed.tsv"
OUT_DIR="${ROOT}/taxprofiling/results/krakenuniq_taxonomy_only_redo"

python - <<'PY'
import pandas as pd
inp = '/home/jonyb/my_things/python_programing/_tmp_krakenuniq_redo/krakenuniq_krakenuniq_standard.tsv'
out = '/home/jonyb/my_things/python_programing/_tmp_krakenuniq_redo/krakenuniq_krakenuniq_standard.transposed.tsv'
m = pd.read_csv(inp, sep='\t').set_index('taxonomy_id').T
m.index.name = 'sample_id'
m.to_csv(out, sep='\t')
print(m.shape)
PY

python "${ROOT}/taxprofiling/tools/analyze_cooccurrence_and_ratios.py" \
  --abundance-table "${TRANSPOSED}" \
  --output-dir "${OUT_DIR}" \
  --sample-column sample_id \
  --max-taxa 40 \
  --ratio-taxa 15 \
  --min-prevalence 0.2 \
  --min-total-abundance 1 \
  --min-joint-nonzero 3

python "${ROOT}/taxprofiling/tools/plot_krakenuniq_cooccurrence.py" \
  --edges "${OUT_DIR}/cooccurrence_edges.csv" \
  --output "${OUT_DIR}/cooccurrence_summary.png"
