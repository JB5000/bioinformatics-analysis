#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <cluster_host> <job_id> <nextflow_log_path>"
  exit 1
fi

HOST="$1"
JOB_ID="$2"
LOG_PATH="$3"

ssh "$HOST" "echo '=== Job ==='; squeue -j $JOB_ID; echo; echo '=== Nextflow tail ==='; tail -40 $LOG_PATH"
