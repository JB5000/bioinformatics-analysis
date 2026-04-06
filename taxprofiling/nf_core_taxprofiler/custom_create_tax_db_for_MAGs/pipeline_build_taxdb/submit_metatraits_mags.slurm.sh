#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --job-name=metatraits39
#SBATCH --chdir=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb
#SBATCH --output=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/%x_%j.out
#SBATCH --error=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/%x_%j.err

set -euo pipefail

PIPELINE_DIR="/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb"
RUN_DIR="${RUN_DIR:-$PIPELINE_DIR/runs/build_taxdb_20260322_182139_corrida_certa}"
BIN_SUMMARY="${BIN_SUMMARY:-/home/jbentes/projects/bioinformatics/nf_core_mag/long_only/nfcore-mag-hybrid-so240416-20260202_084826_from_DAVID/GenomeBinning/bin_summary.tsv}"
OUTPUT_DIR="${OUTPUT_DIR:-$RUN_DIR/metatraits_api_slurm_${SLURM_JOB_ID}}"
SCRIPT_PATH="$PIPELINE_DIR/run_metatraits_mags.py"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "ERROR: script not found: $SCRIPT_PATH" >&2
  exit 1
fi

if [[ ! -d "$RUN_DIR/mags_kraken2" ]]; then
  echo "ERROR: RUN_DIR does not look valid (missing mags_kraken2): $RUN_DIR" >&2
  exit 1
fi

if [[ ! -f "$BIN_SUMMARY" ]]; then
  echo "ERROR: bin summary not found: $BIN_SUMMARY" >&2
  exit 1
fi

export TMPDIR="$HOME/tmp/metatraits_api/${SLURM_JOB_ID}"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
mkdir -p "$TMPDIR"

VERIFY_SSL_FLAG=()
if [[ "${VERIFY_SSL:-0}" == "1" ]]; then
  VERIFY_SSL_FLAG=(--verify-ssl)
fi

echo "Node: $(hostname)"
date
echo "RUN_DIR=$RUN_DIR"
echo "BIN_SUMMARY=$BIN_SUMMARY"
echo "OUTPUT_DIR=$OUTPUT_DIR"
echo "TMPDIR=$TMPDIR"

python3 "$SCRIPT_PATH" \
  --pipeline-dir "$PIPELINE_DIR" \
  --run-dir "$RUN_DIR" \
  --bin-summary "$BIN_SUMMARY" \
  --output-dir "$OUTPUT_DIR" \
  --timeout-sec "${TIMEOUT_SEC:-90}" \
  --max-retries "${MAX_RETRIES:-3}" \
  "${VERIFY_SSL_FLAG[@]}"

echo "Done at $(date)"
echo "Results: $OUTPUT_DIR"
