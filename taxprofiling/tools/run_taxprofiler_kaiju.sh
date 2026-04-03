#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <workdir>"
  exit 1
fi

WORKDIR="$1"
cd "$WORKDIR"

nextflow run nf-core/taxprofiler \
  -profile apptainer \
  -c nextflow.config \
  --input samples_input.csv \
  --databases databases_input.csv
