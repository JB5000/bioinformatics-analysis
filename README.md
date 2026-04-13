# Bioinformatics Analysis Hub

Central repository for bioinformatics workflows, scripts, and project modules.

## Structure
- `taxprofiling/`: taxonomic profiling workflows and scripts
- `mag-assembly/`: MAG assembly workflows and helper scripts
- `mash/`: MASH sketching and comparison utilities
- `common/`: shared utilities
- `docs/`: workflow notes and usage docs

## Recent Updates
- [2026-04-13] - Added `common/scripts/nanopore_gbases_by_date.py` to estimate nanopore gigabases by date and export CSV/HTML/log outputs - Document archived sample-yield visualization workflow.
- [2026-04-13] - Added `docs/nanopore_gbases_by_date.md` with run instructions and output description - Make the utility reproducible by other users.
- [2026-04-13] - Added `common/scripts/plot_bin_quality_hq_mq_lq.py` and `docs/plot_bin_quality_hq_mq_lq.md` for one-shot HQ/MQ/LQ MAG quality plotting - Provide reproducible completeness-vs-contamination visualization with clear class colors and usage notes.

## Notes
This repository is organized to keep multiple bioinformatics projects under one place while preserving domain-specific subfolders.
