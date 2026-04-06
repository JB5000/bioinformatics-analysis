#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --job-name=clowm_auth
#SBATCH --chdir=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb
#SBATCH --output=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/clowm_auth_%j.out
#SBATCH --error=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/clowm_auth_%j.err
set -euo pipefail
export TMPDIR="$HOME/tmp/clowm_auth/${SLURM_JOB_ID}"
mkdir -p "$TMPDIR"

echo "Node: $(hostname)"
date
TOKEN=$(curl -sS -m 25 'https://clowm.bi.denbi.de/api/auth/trial' | tr -d '"\n\r')
echo "token_len=${#TOKEN}"

for payload in \
  "token=$TOKEN" \
  "trial_token=$TOKEN" \
  "jwt=$TOKEN" \
  "token=$TOKEN&bot=" \
  "trial_token=$TOKEN&website="
 do
  echo "--- payload: ${payload:0:80} ---"
  code=$(curl -sS -m 25 -o "$TMPDIR/body.txt" -D "$TMPDIR/hdr.txt" -c "$TMPDIR/cookie.txt" -X POST 'https://clowm.bi.denbi.de/api/auth/trial' -H 'Content-Type: application/x-www-form-urlencoded' --data "$payload" -w '%{http_code}' || true)
  echo "POST /api/auth/trial -> $code"
  grep -i '^location:' "$TMPDIR/hdr.txt" | sed 's/\r$//' || true
  grep -i '^set-cookie:' "$TMPDIR/hdr.txt" | sed 's/\r$//' || true
  code_me=$(curl -sS -m 20 -o "$TMPDIR/me.txt" -b "$TMPDIR/cookie.txt" -w '%{http_code}' 'https://clowm.bi.denbi.de/api/ui/users/me' || true)
  echo "/api/ui/users/me with cookie jar -> $code_me"
  head -c 180 "$TMPDIR/me.txt"; echo
 done

date
