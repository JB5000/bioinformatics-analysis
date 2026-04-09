# KrakenUniq Taxonomy-Only Redo Report

## Run Context
- Date: 2026-04-09
- Input table: `_tmp_krakenuniq_redo/krakenuniq_krakenuniq_standard.transposed.tsv`
- Samples: 52
- Candidate taxa table width: 18611 taxa

## Network Summary
- Selected taxa: 40
- Total edges tested: 780
- Significant edges (q <= 0.05): 599
- Spearman rho range: -0.9408 to 0.9967
- Connected components: 1

## Top Positive Associations
| Taxon Left | Taxon Right | rho | q-value |
|---|---|---:|---:|
| 204455 | 2854170 | 0.9967 | 3.25e-53 |
| 1529069 | 996801 | 0.9936 | 1.97e-46 |
| 571177 | 947919 | 0.9933 | 4.80e-46 |
| 1774273 | 996801 | 0.9904 | 2.15e-42 |
| 335992 | 2563896 | 0.9890 | 5.78e-41 |

## Top Negative Associations
| Taxon Left | Taxon Right | rho | q-value |
|---|---|---:|---:|
| 2268451 | 43989 | -0.9408 | 7.96e-24 |
| 335992 | 43989 | -0.9302 | 3.70e-22 |
| 2563896 | 43989 | -0.9290 | 5.61e-22 |
| 335992 | 111780 | -0.9232 | 3.48e-21 |
| 2563896 | 111780 | -0.9208 | 7.15e-21 |

## Interpretation Notes
- The strongest positive edges suggest taxa groups that repeatedly increase/decrease together across the 52 samples.
- Strong negative edges suggest potential niche partitioning or mutually exclusive dynamics.
- The graph is fully connected with selected taxa, indicating broad shared structure in the selected high-prevalence subset.
- High-degree taxa should be prioritized for downstream ecological hypothesis testing.
