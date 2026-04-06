#!/bin/bash

#SBATCH --partition=bigmem
#SBATCH --nodelist=ceta-gen
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=54
#SBATCH --job-name=taxKaiju
#SBATCH --output=result_%j.out
#SBATCH --error=result_%j.err

module list
set -euo pipefail

# Java 17 auto-detect
if [ -d /usr/lib/jvm/java-17-openjdk-17.0.16.0.8-2.el8.x86_64 ]; then
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-17.0.16.0.8-2.el8.x86_64
elif [ -d /usr/lib/jvm/java-17-openjdk-17.0.15.0.6-2.el8.x86_64 ]; then
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-17.0.15.0.6-2.el8.x86_64
else
    export JAVA_HOME=$(ls -d /usr/lib/jvm/java-17-openjdk-* 2>/dev/null | head -1)
fi
export PATH=$JAVA_HOME/bin:$PATH
export JAVA_CMD=$JAVA_HOME/bin/java

echo "=== Java Configuration ==="
echo "JAVA_HOME: $JAVA_HOME"
echo "Java location: $(which java)"
echo "Java version:"
java -version 2>&1
echo "=========================="
echo ""

# -------------------------------
# Nextflow & Apptainer paths
# -------------------------------
export NXF_APPTAINER_CACHEDIR=/share/apps/share/nextflow/apptainer_cache
export NXF_TEMP=/home/jbentes/.nextflow/tmp
export APPTAINER_BIND="/share/data,/home,/home2,/share/apps"


# -------------------------------
# TEMP DIR (CRITICAL FIX)
# Use per-job tmp inside work/
# -------------------------------
WORK_BASE=/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/kaiju_nr_euk/work
export TMPDIR=$WORK_BASE/tmp_${SLURM_JOB_ID}
mkdir -p "$TMPDIR"

export _JAVA_OPTIONS="-Djava.io.tmpdir=$TMPDIR"
export APPTAINER_TMPDIR=$TMPDIR

# -------------------------------
# Output directory
# -------------------------------
OUTDIR="results/run-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTDIR"

# -------------------------------
# Cleanup handlers
# -------------------------------
cleanup_tmp() {
    echo "Cleaning TMPDIR: $TMPDIR"
    rm -rf "$TMPDIR"
}

cleanup_logs() {
    echo "Job finished. Moving Slurm logs to $OUTDIR..."
    mv "result_${SLURM_JOB_ID}.out" "$OUTDIR/" || true
    mv "result_${SLURM_JOB_ID}.err" "$OUTDIR/" || true
}

trap cleanup_tmp EXIT
trap cleanup_logs EXIT


# -------------------------------
# Run Nextflow
# -------------------------------
nextflow run nf-core/taxprofiler -r 1.2.4 \
  -profile apptainer \
  -c nextflow.config \
  --input samples_input.csv \
  --databases databases_input.csv \
  --outdir "$OUTDIR" \
  --perform_shortread_qc \
  --shortread_qc_tool fastp \
  --shortread_qc_mergepairs \
  --perform_shortread_complexityfilter \
  --shortread_complexityfilter_tool fastp \
  --run_kaiju \
  --run_krona \
  --run_profile_standardisation \
  --max_cpus $SLURM_CPUS_PER_TASK
  
echo "Job finished at $(date)"
