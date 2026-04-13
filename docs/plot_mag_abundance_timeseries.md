# MAG Abundance Time-Series Plot

## Description
Generates a PNG line plot showing MAG (Metagenome-Assembled Genome) abundance across multiple samples over time. Each MAG is represented as a separate line, with sample dates displayed on the X-axis.

## Features
- **All dates visible**: Every sample date appears on the X-axis (no sampling/thinning)
- **Automatic date parsing**: Extracts dates and micro-replicate IDs from column names (e.g., `20260103_micro_1`)
- **Sorted chronologically**: Samples ordered by date, then by micro-replicate ID
- **Legend handling**: Duplicate date labels are disambiguated with `#` numbering
- **High resolution**: 220 DPI output for publication-ready figures
- **Grid overlay**: Semi-transparent grid for easier reading

## Input Format
Expects a tab-separated file with:
- First column: `Genome` (MAG names; row "unmapped" is filtered out)
- Other columns: Named as `<DATE_IDENTIFIER> Relative Abundance` (e.g., `20260103_micro_1 Relative Abundance`)

## Output Files
- **PNG**: Static line plot (X=sample dates, Y=relative abundance %)
- **LOG**: Plain text log with metadata (input path, output path, sample count, MAG count)

## Usage Example
```bash
python3 plot_mag_abundance_timeseries.py
```

Currently uses hardcoded paths:
- **Input**: `/home/jbentes/projects/bioinformatics/storage_of_results/resultados_coverm/matriz_abundancia_ria_formosa.tsv`
- **Output**: `/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/mag_abundance_timeseries_all_dates.png`

## Dependencies
- Python 3.7+
- `pandas`: Data frame handling
- `matplotlib`: PNG rendering (via Agg backend for headless environments)

## Output Example
A line plot with:
- 51+ sample time points on X-axis
- 11+ MAG abundance lines (different colors, alpha transparency for overlap visibility)
- Title: "Abundancia dos MAGs ao longo das samples"
- X-axis label: "Samples (todas as datas)"
- Y-axis label: "Abundancia Relativa (%)"

---
**Created**: 2026-04-13 | **Updated**: 2026-04-13
