#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <samples_csv> <databases_csv>"
  exit 1
fi

samples="$1"
databases="$2"

[[ -f "$samples" ]] || { echo "Missing samples file: $samples"; exit 1; }
[[ -f "$databases" ]] || { echo "Missing databases file: $databases"; exit 1; }

head -n 1 "$samples" | grep -qi 'sample' || { echo "Samplesheet header check failed"; exit 1; }
head -n 1 "$databases" | grep -qi 'db' || echo "Warning: databases header may not include 'db'"

echo "Input validation passed"
