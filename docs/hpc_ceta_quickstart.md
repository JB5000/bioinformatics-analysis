# CETA HPC Quickstart

## Check job status
- `squeue -j <JOB_ID>`
- `sacct -j <JOB_ID> --format=JobID,State,Elapsed,NodeList`

## Inspect nextflow log
- `tail -50 .nextflow.log`

## Inspect one task workdir
- `ls -lah work/<hash>/<hash>/`
- `tail -50 work/<hash>/<hash>/.command.err`
