#!/usr/bin/env python3
"""Compute co-occurrence networks and ratio-based environmental associations.

The script accepts a taxonomic abundance table in wide or long format and, optionally,
an environmental metadata table. It produces:

- a pairwise co-occurrence edge list;
- a node summary with simple graph metrics;
- a ratio matrix for the most abundant taxa;
- ratio-to-environment association tables;
- a compact JSON summary of the run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from itertools import combinations
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests


SAMPLE_CANDIDATES = (
    "sample",
    "sample_id",
    "sampleid",
    "id",
    "run_accession",
    "run",
)

TAXON_CANDIDATES = (
    "taxon",
    "taxon_name",
    "taxonomy",
    "species",
    "organism",
    "name",
    "feature",
)

ABUNDANCE_CANDIDATES = (
    "abundance",
    "count",
    "counts",
    "reads",
    "value",
    "relative_abundance",
    "rel_abundance",
)


def normalize_name(value: str) -> str:
    text = str(value).strip().lower()
    for char in (" ", "-", "/", "\\", ":", ";", "(", ")", "[", "]", ","):
        text = text.replace(char, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _resolve_ssh_alias(hostname: str) -> tuple[str, str | None, int | None]:
    """Resolve SSH host aliases using `ssh -G`.

    Returns a tuple with (hostname, user, port).
    """
    try:
        output = subprocess.check_output(
            ["ssh", "-G", hostname],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except Exception:
        return hostname, None, None

    resolved_host = hostname
    user: str | None = None
    port: int | None = None
    for line in output.splitlines():
        if not line:
            continue
        key, _, value = line.partition(" ")
        key = key.strip().lower()
        value = value.strip()
        if key == "hostname" and value:
            resolved_host = value
        elif key == "user" and value:
            user = value
        elif key == "port" and value.isdigit():
            port = int(value)
    return resolved_host, user, port


def _read_remote_table(path_str: str, suffix: str, sheet_name: str | None) -> pd.DataFrame:
    try:
        import fsspec
    except ImportError as exc:
        raise RuntimeError(
            "Reading remote URIs requires `fsspec`. Install it with `pip install fsspec sshfs`."
        ) from exc

    parsed = urlparse(path_str)
    if parsed.scheme == "ssh" and parsed.hostname:
        host, default_user, default_port = _resolve_ssh_alias(parsed.hostname)
        user = parsed.username or default_user
        port = parsed.port or default_port
        auth = f"{user}@" if user else ""
        port_part = f":{port}" if port else ""
        normalized_uri = f"ssh://{auth}{host}{port_part}{parsed.path}"
    else:
        normalized_uri = path_str

    if suffix in {".csv", ".tsv", ".txt"}:
        if suffix == ".tsv":
            return pd.read_csv(normalized_uri, sep="\t", storage_options={})
        return pd.read_csv(normalized_uri, sep=None, engine="python", storage_options={})
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        with fsspec.open(normalized_uri, mode="rb") as handle:
            return pd.read_excel(handle, sheet_name=sheet_name or 0)
    raise ValueError(f"Unsupported input format: {suffix}")


def load_table(path: str | Path, sheet_name: str | None = None) -> pd.DataFrame:
    path_str = str(path)
    suffix = Path(path_str).suffix.lower()
    parsed = urlparse(path_str)

    if parsed.scheme and parsed.scheme != "file":
        return _read_remote_table(path_str, suffix, sheet_name)

    local_path = Path(path_str)
    if suffix in {".csv", ".tsv", ".txt"}:
        if suffix == ".tsv":
            return pd.read_csv(local_path, sep="\t")
        return pd.read_csv(local_path, sep=None, engine="python")
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(local_path, sheet_name=sheet_name or 0)
    raise ValueError(f"Unsupported input format: {suffix}")


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.copy()
    renamed.columns = [normalize_name(column) for column in renamed.columns]
    return renamed


def first_matching_column(columns: Iterable[str], candidates: tuple[str, ...]) -> str | None:
    normalized = [normalize_name(column) for column in columns]
    for candidate in candidates:
        if candidate in normalized:
            return columns[normalized.index(candidate)]
    return None


def detect_sample_column(frame: pd.DataFrame, preferred: str | None = None) -> str:
    if preferred:
        normalized_preferred = normalize_name(preferred)
        if normalized_preferred in frame.columns:
            return normalized_preferred
    match = first_matching_column(frame.columns, SAMPLE_CANDIDATES)
    if match is not None:
        return match
    raise ValueError("Could not detect a sample column. Use --sample-column.")


def detect_long_format_columns(frame: pd.DataFrame, sample_column: str) -> tuple[str, str] | None:
    taxon_column = first_matching_column(frame.columns, TAXON_CANDIDATES)
    abundance_column = first_matching_column(frame.columns, ABUNDANCE_CANDIDATES)
    if taxon_column and abundance_column:
        return taxon_column, abundance_column
    if {"taxon", "abundance"}.issubset(frame.columns):
        return "taxon", "abundance"
    if {"species", "count"}.issubset(frame.columns):
        return "species", "count"
    if sample_column in frame.columns and taxon_column and abundance_column:
        return taxon_column, abundance_column
    return None


def prepare_abundance_matrix(
    frame: pd.DataFrame,
    sample_column: str,
    taxon_column: str | None = None,
    abundance_column: str | None = None,
) -> pd.DataFrame:
    data = normalize_columns(frame)
    sample_column = normalize_name(sample_column)
    if sample_column not in data.columns:
        raise ValueError(f"Sample column '{sample_column}' not found after normalization.")

    if taxon_column and abundance_column:
        taxon_column = normalize_name(taxon_column)
        abundance_column = normalize_name(abundance_column)
    else:
        detected = detect_long_format_columns(data, sample_column)
        if detected is not None:
            taxon_column, abundance_column = detected
            taxon_column = normalize_name(taxon_column)
            abundance_column = normalize_name(abundance_column)

    if taxon_column and abundance_column and taxon_column in data.columns and abundance_column in data.columns:
        long_table = data[[sample_column, taxon_column, abundance_column]].copy()
        long_table[sample_column] = long_table[sample_column].astype(str).str.strip()
        long_table[taxon_column] = long_table[taxon_column].astype(str).str.strip()
        long_table[abundance_column] = pd.to_numeric(long_table[abundance_column], errors="coerce").fillna(0.0)
        wide_table = (
            long_table.pivot_table(
                index=sample_column,
                columns=taxon_column,
                values=abundance_column,
                aggfunc="sum",
                fill_value=0.0,
            )
            .sort_index(axis=1)
            .astype(float)
        )
        wide_table.index.name = sample_column
        return wide_table

    wide_table = data.copy()
    wide_table[sample_column] = wide_table[sample_column].astype(str).str.strip()
    wide_table = wide_table.set_index(sample_column)
    numeric_table = wide_table.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    numeric_table = numeric_table.loc[:, (numeric_table.sum(axis=0) > 0)]
    if numeric_table.empty:
        raise ValueError("No numeric abundance columns were detected.")
    return numeric_table


def select_taxa(table: pd.DataFrame, min_prevalence: float, min_total_abundance: float, max_taxa: int) -> list[str]:
    prevalence = (table > 0).sum(axis=0) / float(len(table))
    totals = table.sum(axis=0)
    keep = totals[(prevalence >= min_prevalence) & (totals >= min_total_abundance)]
    keep = keep.sort_values(ascending=False).head(max_taxa)
    return keep.index.tolist()


def spearman_pairwise(table: pd.DataFrame, taxa: list[str], min_joint_nonzero: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for left, right in combinations(taxa, 2):
        pair = table[[left, right]].dropna()
        joint_nonzero = int(((pair[left] > 0) & (pair[right] > 0)).sum())
        if joint_nonzero < min_joint_nonzero:
            continue
        rho, p_value = spearmanr(pair[left], pair[right])
        if np.isnan(rho) or np.isnan(p_value):
            continue
        rows.append(
            {
                "taxon_left": left,
                "taxon_right": right,
                "rho": float(rho),
                "p_value": float(p_value),
                "samples": int(len(pair)),
                "joint_nonzero": joint_nonzero,
            }
        )
    edges = pd.DataFrame(rows)
    if not edges.empty:
        edges["q_value"] = multipletests(edges["p_value"].to_numpy(), method="fdr_bh")[1]
        edges["abs_rho"] = edges["rho"].abs()
        edges = edges.sort_values(["q_value", "abs_rho"], ascending=[True, False]).reset_index(drop=True)
    return edges


def build_graph(edges: pd.DataFrame, selected_taxa: list[str]) -> tuple[pd.DataFrame, dict[str, object]]:
    graph = nx.Graph()
    graph.add_nodes_from(selected_taxa)
    for _, row in edges.iterrows():
        graph.add_edge(
            row["taxon_left"],
            row["taxon_right"],
            rho=float(row["rho"]),
            q_value=float(row["q_value"]),
            weight=float(abs(row["rho"])),
        )

    degree = dict(graph.degree())
    weighted_degree = dict(graph.degree(weight="weight"))
    component_map: dict[str, int] = {}
    for index, component in enumerate(nx.connected_components(graph)):
        for node in component:
            component_map[node] = index

    node_rows = []
    for node in graph.nodes:
        node_rows.append(
            {
                "taxon": node,
                "degree": int(degree.get(node, 0)),
                "weighted_degree": float(weighted_degree.get(node, 0.0)),
                "component": int(component_map.get(node, -1)),
            }
        )

    summary = {
        "nodes": int(graph.number_of_nodes()),
        "edges": int(graph.number_of_edges()),
        "connected_components": int(nx.number_connected_components(graph)),
        "density": float(nx.density(graph)) if graph.number_of_nodes() > 1 else 0.0,
    }
    return pd.DataFrame(node_rows).sort_values(["degree", "weighted_degree"], ascending=[False, False]), summary


def build_ratio_matrix(table: pd.DataFrame, taxa: list[str], pseudocount: float) -> pd.DataFrame:
    ratio_series = []
    for left, right in combinations(taxa, 2):
        column_name = f"{left}__over__{right}"
        ratio_series.append(
            pd.Series(
                np.log10((table[left] + pseudocount) / (table[right] + pseudocount)),
                index=table.index,
                name=column_name,
            )
        )
    if not ratio_series:
        return pd.DataFrame(index=table.index)
    return pd.concat(ratio_series, axis=1)


def metadata_numeric_columns(frame: pd.DataFrame, sample_column: str) -> pd.DataFrame:
    data = normalize_columns(frame)
    sample_column = normalize_name(sample_column)
    if sample_column not in data.columns:
        raise ValueError(f"Metadata sample column '{sample_column}' not found.")
    data[sample_column] = data[sample_column].astype(str).str.strip()
    numeric = data.drop(columns=[sample_column]).apply(pd.to_numeric, errors="coerce")
    numeric = numeric.loc[:, numeric.notna().sum(axis=0) >= 3]
    numeric.index = data[sample_column]
    return numeric


def ratio_environment_associations(
    ratios: pd.DataFrame,
    metadata: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    common_index = ratios.index.intersection(metadata.index)
    if common_index.empty:
        return pd.DataFrame()

    aligned_ratios = ratios.loc[common_index]
    aligned_metadata = metadata.loc[common_index]
    for ratio_name in aligned_ratios.columns:
        ratio_series = aligned_ratios[ratio_name]
        for variable in aligned_metadata.columns:
            env_series = aligned_metadata[variable]
            pair = pd.concat([ratio_series, env_series], axis=1).dropna()
            if len(pair) < 5:
                continue
            rho, p_value = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
            if np.isnan(rho) or np.isnan(p_value):
                continue
            rows.append(
                {
                    "ratio": ratio_name,
                    "environment_variable": variable,
                    "rho": float(rho),
                    "p_value": float(p_value),
                    "samples": int(len(pair)),
                }
            )

    results = pd.DataFrame(rows)
    if results.empty:
        return results
    results["q_value"] = multipletests(results["p_value"].to_numpy(), method="fdr_bh")[1]
    results["abs_rho"] = results["rho"].abs()
    results = results.sort_values(["q_value", "abs_rho"], ascending=[True, False]).reset_index(drop=True)
    return results.head(top_n)


def write_outputs(
    output_dir: Path,
    edges: pd.DataFrame,
    nodes: pd.DataFrame,
    ratios: pd.DataFrame,
    associations: pd.DataFrame,
    summary: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    edges.to_csv(output_dir / "cooccurrence_edges.csv", index=False)
    nodes.to_csv(output_dir / "cooccurrence_nodes.csv", index=False)
    ratios.to_csv(output_dir / "ratio_matrix.csv")
    associations.to_csv(output_dir / "ratio_environment_associations.csv", index=False)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--abundance-table", required=True, type=str, help="CSV/TSV/XLSX with taxonomic abundances.")
    parser.add_argument("--metadata", type=str, help="Optional environmental metadata table.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory where outputs will be written.")
    parser.add_argument("--sheet-name", help="Excel sheet name for the abundance table.")
    parser.add_argument("--metadata-sheet", help="Excel sheet name for the metadata table.")
    parser.add_argument("--sample-column", help="Sample identifier column in the abundance table.")
    parser.add_argument("--metadata-sample-column", help="Sample identifier column in the metadata table.")
    parser.add_argument("--taxon-column", help="Long-format taxon column.")
    parser.add_argument("--abundance-column", help="Long-format abundance column.")
    parser.add_argument("--min-prevalence", type=float, default=0.20, help="Minimum prevalence fraction for taxa selection.")
    parser.add_argument("--min-total-abundance", type=float, default=1.0, help="Minimum total abundance for taxa selection.")
    parser.add_argument("--max-taxa", type=int, default=40, help="Maximum taxa used for the co-occurrence network.")
    parser.add_argument("--ratio-taxa", type=int, default=15, help="Number of top taxa used to generate pairwise ratios.")
    parser.add_argument("--min-joint-nonzero", type=int, default=3, help="Minimum joint non-zero samples for an edge.")
    parser.add_argument("--ratio-pseudocount", type=float, default=1e-6, help="Pseudocount used in log-ratio calculations.")
    parser.add_argument("--top-associations", type=int, default=100, help="Maximum ratio-environment associations to retain.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    abundance_frame = load_table(args.abundance_table, args.sheet_name)
    sample_column = detect_sample_column(normalize_columns(abundance_frame), args.sample_column)
    abundance_table = prepare_abundance_matrix(
        abundance_frame,
        sample_column=sample_column,
        taxon_column=args.taxon_column,
        abundance_column=args.abundance_column,
    )

    selected_taxa = select_taxa(
        abundance_table,
        min_prevalence=args.min_prevalence,
        min_total_abundance=args.min_total_abundance,
        max_taxa=args.max_taxa,
    )
    if len(selected_taxa) < 2:
        raise ValueError("Not enough taxa passed the filters to build a co-occurrence network.")

    cooccurrence_table = abundance_table[selected_taxa].astype(float)
    relative_table = cooccurrence_table.div(cooccurrence_table.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    edges = spearman_pairwise(relative_table, selected_taxa, min_joint_nonzero=args.min_joint_nonzero)
    nodes, graph_summary = build_graph(edges, selected_taxa)

    ratio_taxa = selected_taxa[: min(args.ratio_taxa, len(selected_taxa))]
    ratio_matrix = build_ratio_matrix(cooccurrence_table, ratio_taxa, pseudocount=args.ratio_pseudocount)

    associations = pd.DataFrame()
    if args.metadata is not None:
        metadata_frame = load_table(args.metadata, args.metadata_sheet)
        metadata_sample_column = args.metadata_sample_column or detect_sample_column(normalize_columns(metadata_frame))
        metadata = metadata_numeric_columns(metadata_frame, metadata_sample_column)
        associations = ratio_environment_associations(ratio_matrix, metadata, top_n=args.top_associations)

    summary = {
        "abundance_table": str(args.abundance_table),
        "metadata": str(args.metadata) if args.metadata else None,
        "selected_taxa": len(selected_taxa),
        "ratio_columns": int(ratio_matrix.shape[1]),
        "cooccurrence_edges": int(edges.shape[0]),
        **graph_summary,
    }
    write_outputs(args.output_dir, edges, nodes, ratio_matrix, associations, summary)

    graph_path = args.output_dir / "cooccurrence_network.gexf"
    graph = nx.Graph()
    graph.add_nodes_from(selected_taxa)
    for _, row in edges.iterrows():
        graph.add_edge(row["taxon_left"], row["taxon_right"], rho=float(row["rho"]), q_value=float(row["q_value"]))
    nx.write_gexf(graph, graph_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())