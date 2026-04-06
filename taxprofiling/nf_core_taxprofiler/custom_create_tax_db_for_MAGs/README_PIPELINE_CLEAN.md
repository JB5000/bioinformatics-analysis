# Clean Custom MAG Taxonomy Pipeline

This folder is now organized into two independent Slurm pipelines:

- `pipeline_build_taxdb/`: receives an `nf-core/mag` output directory, discovers bin summary TSV, selects HQ MAGs, and builds a custom DB with `nf-core/createtaxdb`.
- `pipeline_run_taxprofiler/`: runs `nf-core/taxprofiler` against a custom DB produced by the first pipeline.

## 1) Build custom DB from nf-core/mag output

Go to:

```bash
cd /home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb
```

Submit:

```bash
sbatch --export=ALL,NFCORE_MAG_OUTDIR=/path/to/nfcore_mag_outdir submit_build_taxdb.slurm.sh
```

Optional thresholds:

```bash
sbatch --export=ALL,NFCORE_MAG_OUTDIR=/path/to/nfcore_mag_outdir,MIN_COMPLETENESS=90,MAX_CONTAMINATION=5 submit_build_taxdb.slurm.sh
```

Output run folder:

- `pipeline_build_taxdb/runs/build_taxdb_<timestamp>/`
- custom DB in `.../custom_mag_db/`

## 2) Run taxprofiler with that custom DB

Go to:

```bash
cd /home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_run_taxprofiler
```

Submit:

```bash
sbatch --export=ALL,READSHEET=/path/to/samplesheet.csv,DB_RUN_DIR=/path/to/pipeline_build_taxdb/runs/build_taxdb_<timestamp> submit_taxprofiler_with_custom_db.slurm.sh
```

For Nanopore (recommended default), Bracken is disabled.
To force Bracken:

```bash
sbatch --export=ALL,READSHEET=/path/to/samplesheet.csv,DB_RUN_DIR=/path/to/build_taxdb_xxx,RUN_BRACKEN=true submit_taxprofiler_with_custom_db.slurm.sh
```

Output run folder:

- `pipeline_run_taxprofiler/runs/taxprofiler_<timestamp>/resultados_taxprofiler`

## Notes

- Logs always go to the directory where `sbatch` is called (`%x_%j.out` and `%x_%j.err`).
- Old mixed files were moved to `legacy_before_refactor_20260319/`.
