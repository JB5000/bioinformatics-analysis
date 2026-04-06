#!/bin/bash
#SBATCH --partition=all
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00
#SBATCH --job-name=mt_connect
#SBATCH --chdir=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb
#SBATCH --output=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/mt_connect_%j.out
#SBATCH --error=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/mt_connect_%j.err
set -euo pipefail
export TMPDIR="$HOME/tmp/metatraits/${SLURM_JOB_ID}"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
mkdir -p "$TMPDIR"
echo "Node: $(hostname)"
date
python3 - <<'PY'
import requests, urllib3, time
urllib3.disable_warnings()
for url in [
    "https://metatraits.embl.de/documentation",
    "https://metatraits.embl.de/api/v1/traits/taxonomy/562",
]:
    t0 = time.time()
    try:
        r = requests.get(url, timeout=20, verify=False)
        print("OK", url, r.status_code, len(r.text), round(time.time() - t0, 2))
        print(r.text[:120].replace("\n", " "))
    except Exception as e:
        print("ERR", url, type(e).__name__, str(e), round(time.time() - t0, 2))
PY
