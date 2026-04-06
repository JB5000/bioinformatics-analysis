#!/bin/bash
#SBATCH --partition=bigmem
#SBATCH --nodelist=ceta-gen
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=100G
#SBATCH --time=24:00:00
#SBATCH --job-name=runTaxprofiler
#SBATCH --chdir=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_run_taxprofiler
#SBATCH --output=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_run_taxprofiler/%x_%j.out
#SBATCH --error=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_run_taxprofiler/%x_%j.err

set -euo pipefail
module list

SCRIPT_DIR="/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_run_taxprofiler"

READSHEET="${READSHEET:-}"
if [[ -z "$READSHEET" ]]; then
  echo "ERROR: set READSHEET to samplesheet CSV path" >&2
  exit 1
fi

DB_RUN_DIR="${DB_RUN_DIR:-}"
if [[ -z "$DB_RUN_DIR" ]]; then
  echo "ERROR: set DB_RUN_DIR to pipeline_build_taxdb/runs/build_taxdb_<tag> directory" >&2
  exit 1
fi

RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/runs/taxprofiler_${RUN_TAG}}"
OUTDIR="$RUN_DIR/resultados_taxprofiler"
mkdir -p "$RUN_DIR"

if [ -d /usr/lib/jvm/java-17-openjdk-17.0.16.0.8-2.el8.x86_64 ]; then
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-17.0.16.0.8-2.el8.x86_64
elif [ -d /usr/lib/jvm/java-17-openjdk-17.0.15.0.6-2.el8.x86_64 ]; then
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-17.0.15.0.6-2.el8.x86_64
else
    export JAVA_HOME=$(ls -d /usr/lib/jvm/java-17-openjdk-* 2>/dev/null | head -1)
fi
export PATH="$JAVA_HOME/bin:$PATH"
export JAVA_CMD="$JAVA_HOME/bin/java"

export NXF_VER=25.10.4
export NXF_HOME="$HOME/.nextflow"
export NXF_TEMP="$HOME/.nextflow/tmp"
export NXF_APPTAINER_CACHEDIR=/share/apps/share/nextflow/apptainer_cache
export NXF_SINGULARITY_CACHEDIR="$NXF_APPTAINER_CACHEDIR"
export APPTAINER_CACHEDIR="$NXF_APPTAINER_CACHEDIR"

export TMPDIR="$HOME/tmp/taxprofiler/${SLURM_JOB_ID}"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
export APPTAINER_TMPDIR="$TMPDIR"
export _JAVA_OPTIONS="-Djava.io.tmpdir=$TMPDIR"
mkdir -p "$TMPDIR" "$NXF_TEMP" "$NXF_APPTAINER_CACHEDIR"

# Resolve database directories created by nf-core/createtaxdb output.
KRAKEN_DB_DIR="$(find "$DB_RUN_DIR/custom_mag_db/kraken2" -mindepth 1 -maxdepth 1 -type d | head -n 1 || true)"
BRACKEN_DB_DIR="$(find "$DB_RUN_DIR/custom_mag_db/bracken" -mindepth 1 -maxdepth 1 -type d | head -n 1 || true)"

if [[ -z "$KRAKEN_DB_DIR" ]]; then
  echo "ERROR: could not find kraken2 DB under $DB_RUN_DIR/custom_mag_db/kraken2" >&2
  exit 1
fi

DATABASES_CSV="$RUN_DIR/databases-taxprofiler.custom.csv"
{
  echo "tool,db_name,db_params,db_type,db_path"
  echo "kraken2,$(basename "$KRAKEN_DB_DIR"),,,$KRAKEN_DB_DIR"
  if [[ -n "$BRACKEN_DB_DIR" ]]; then
    echo "bracken,$(basename "$BRACKEN_DB_DIR"),,,$BRACKEN_DB_DIR"
  fi
} > "$DATABASES_CSV"

RUN_BRACKEN="${RUN_BRACKEN:-false}"

echo "Using READSHEET: $READSHEET"
echo "Using DATABASES_CSV: $DATABASES_CSV"
echo "Using OUTDIR: $OUTDIR"
echo "Using RUN_BRACKEN: $RUN_BRACKEN"

if [[ "$RUN_BRACKEN" == "true" ]]; then
  BRACKEN_FLAGS="--run_bracken"
else
  BRACKEN_FLAGS="--run_bracken false"
fi

nextflow run nf-core/taxprofiler -r 1.2.4 \
  -profile apptainer \
  --input "$READSHEET" \
  --databases "$DATABASES_CSV" \
  --run_kraken2 \
  $BRACKEN_FLAGS \
  --outdir "$OUTDIR" \
  -resume

echo "Taxprofiler finished at $(date)"
echo "Run directory: $RUN_DIR"
