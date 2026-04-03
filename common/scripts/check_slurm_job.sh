#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <cluster_host> <job_id>"
  exit 1
fi

HOST="$1"
JOB_ID="$2"

ssh "$HOST" "echo '=== squeue ==='; squeue -j $JOB_ID; echo; echo '=== sacct ==='; sacct -j $JOB_ID --format=JobID,State,Elapsed,NodeList | sed -n '1,8p'"
