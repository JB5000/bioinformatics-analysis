# plot_bin_quality_hq_mq_lq.py

Small utility to generate one PNG scatter plot for all bins from a `bin_summary.tsv` table.

## What It Does
- Reads a TSV with bin quality columns (`bin`, `completeness`/`completeness_checkm2`, `contamination`/`contamination_checkm2`).
- Creates one plot with:
  - x-axis: `Completeness (%)`
  - y-axis: `Contamination (%)`
- Colors all points by quality class:
  - `HQ`: completeness >= 90 and contamination <= 5
  - `MQ`: completeness >= 50 and contamination <= 10 (excluding HQ)
  - `LQ`: all remaining bins
- Saves a `.log` file in the same folder as output.

## How To Run
From repository root:

```bash
python3 common/scripts/plot_bin_quality_hq_mq_lq.py \
  --input-tsv /path/to/GenomeBinning/bin_summary.tsv
```

Optional explicit output paths:

```bash
python3 common/scripts/plot_bin_quality_hq_mq_lq.py \
  --input-tsv /path/to/GenomeBinning/bin_summary.tsv \
  --output-png /path/to/output/bin_summary_all_bins_HQ_MQ_LQ_colored.png \
  --log-file /path/to/output/bin_summary_all_bins_HQ_MQ_LQ_colored.log
```

## Output
Default output files (next to input TSV):
- `bin_summary_all_bins_HQ_MQ_LQ_colored.png`
- `bin_summary_all_bins_HQ_MQ_LQ_colored.log`
