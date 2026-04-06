#!/bin/bash
#SBATCH --partition=bigmem
#SBATCH --nodelist=ceta-gen
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=100G
#SBATCH --time=24:00:00
#SBATCH --job-name=buildTaxDB
#SBATCH --chdir=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb
#SBATCH --output=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/%x_%j.out
#SBATCH --error=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb/%x_%j.err

set -euo pipefail
module list || true

# Use submit dir first; avoid using spool path from BASH_SOURCE in Slurm context.
SCRIPT_DIR="/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb"
NFCORE_MAG_OUTDIR="${NFCORE_MAG_OUTDIR:-/home/jbentes/projects/bioinformatics/nf_core_mag/long_only/nfcore-mag-hybrid-so240416-20260202_084826_from_DAVID}"
export NFCORE_MAG_OUTDIR
if [[ -z "$NFCORE_MAG_OUTDIR" ]]; then
  echo "ERROR: set NFCORE_MAG_OUTDIR to the nf-core/mag output directory" >&2
  exit 1
fi

if [[ "$NFCORE_MAG_OUTDIR" == "/path/to/nfcore_mag_outdir" || "$NFCORE_MAG_OUTDIR" == /path/to/* ]]; then
  echo "ERROR: NFCORE_MAG_OUTDIR is still using a placeholder: $NFCORE_MAG_OUTDIR" >&2
  echo "Use the real cluster path, for example: /home/jbentes/projects/bioinformatics/nf_core_mag/<run_dir>" >&2
  exit 1
fi

if [[ "$NFCORE_MAG_OUTDIR" == ssh://* ]]; then
  echo "ERROR: NFCORE_MAG_OUTDIR must be a cluster filesystem path, not an ssh:// URI" >&2
  echo "Use: /home/jbentes/..." >&2
  exit 1
fi

if [[ ! -d "$NFCORE_MAG_OUTDIR" ]]; then
  echo "ERROR: NFCORE_MAG_OUTDIR does not exist or is not a directory: $NFCORE_MAG_OUTDIR" >&2
  exit 1
fi

echo "Using NFCORE_MAG_OUTDIR: $NFCORE_MAG_OUTDIR"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/runs/build_taxdb_${RUN_TAG}}"
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

export TMPDIR="$HOME/tmp/createtaxdb/${SLURM_JOB_ID}"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
export APPTAINER_TMPDIR="$TMPDIR"
export _JAVA_OPTIONS="-Djava.io.tmpdir=$TMPDIR"
mkdir -p "$TMPDIR" "$NXF_TEMP" "$NXF_APPTAINER_CACHEDIR"

python3 "$SCRIPT_DIR/discover_and_prepare_hq_mags_v2_fast.py" \
  --nfcore-mag-outdir "$NFCORE_MAG_OUTDIR" \
  --run-dir "$RUN_DIR" \
  --max-contamination "${MAX_CONTAMINATION:-5}" \
  --index-cache "$RUN_DIR/.fasta_index_cache.json" \
  --min-completeness "${MIN_COMPLETENESS:-90}"

# Abort early if there are no MAG entries besides the header.
if [[ ! -s "$RUN_DIR/mags_input_kraken.csv" ]] || [[ $(wc -l < "$RUN_DIR/mags_input_kraken.csv") -le 1 ]]; then
  echo "ERROR: $RUN_DIR/mags_input_kraken.csv has no MAG rows. Aborting createTaxDB run." >&2
  exit 2
fi

NF_FIX_CONFIG="$RUN_DIR/createtaxdb_apptainer_fix.config"
cat > "$NF_FIX_CONFIG" << CFG
apptainer {
  pullTimeout = '120m'
}
CFG

nextflow run nf-core/createtaxdb -r 2.1.0 \
  -profile apptainer \
  -c "$NF_FIX_CONFIG" \
  --input "$RUN_DIR/mags_input_kraken.csv" \
  --build_kraken2 \
  --build_bracken \
  --dbname "${DB_NAME:-custom_mag_db}" \
  --namesdmp "$RUN_DIR/taxonomy_ficticia/names.dmp" \
  --nodesdmp "$RUN_DIR/taxonomy_ficticia/nodes.dmp" \
  --accession2taxid "$RUN_DIR/taxonomy_ficticia/acc2tax.tsv" \
  --generate_downstream_samplesheets true \
  --generate_pipeline_samplesheets taxprofiler \
  --skip_multiqc \
  --outdir "$RUN_DIR/custom_mag_db"

echo "CreateTaxDB finished at $(date)"
echo "Run directory: $RUN_DIR"
echo "Custom DB: $RUN_DIR/custom_mag_db"
