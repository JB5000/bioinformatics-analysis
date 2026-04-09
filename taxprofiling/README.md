# Tax Profiling Module

This folder stores scripts and configurations for nf-core/taxprofiler runs.

## Current content
- KrakenUniq profile wrapper
- Kaiju profile wrapper
- Custom MAG taxdb integration scripts

## Analysis helpers
- `tools/analyze_cooccurrence_and_ratios.py`: builds a co-occurrence network from a taxonomic abundance table and scores species-ratio descriptors against environmental metadata.
- `tools/plot_krakenuniq_cooccurrence.py`: creates a quick visual summary (rho distribution + top associations).
- `docs/krakenuniq_cooccurrence_workflow.md`: step-by-step KrakenUniq taxonomy-only workflow.
- `docs/krakenuniq_taxonomy_only_redo_report.md`: results summary and interpretation notes from the latest redo.
