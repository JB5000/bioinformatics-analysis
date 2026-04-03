#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <input_dir_with_fastq> <output_prefix>"
  exit 1
fi

INPUT_DIR="$1"
OUTPUT_PREFIX="$2"

mkdir -p "$(dirname "$OUTPUT_PREFIX")"

find "$INPUT_DIR" -maxdepth 1 -type f \( -name '*.fastq' -o -name '*.fastq.gz' -o -name '*.fq' -o -name '*.fq.gz' \) | sort > "${OUTPUT_PREFIX}.files.txt"

mash sketch -k 21 -s 10000 -l "${OUTPUT_PREFIX}.files.txt" -o "${OUTPUT_PREFIX}"
mash dist "${OUTPUT_PREFIX}.msh" "${OUTPUT_PREFIX}.msh" > "${OUTPUT_PREFIX}.dist.tsv"
