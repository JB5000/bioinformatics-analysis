#!/usr/bin/env python3
"""
Run MetaTraits API annotation for the 39 MAG FASTA files prepared in pipeline_build_taxdb.

Outputs:
- mag_taxid_mapping.csv
- mag_api_status.csv
- mag_traits_long.csv
- mag_traits_summary.csv
- trait_expression_over_time.csv
- report.md
- report.html
- raw_api/<taxid>.json
"""

import argparse
import json
import math
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests

try:
    import urllib3
except Exception:  # pragma: no cover
    urllib3 = None


ACCESSION_RE = re.compile(r"\b(GCA|GCF)_\d+\.\d+\b")
RANK_PREFIXES = ("d", "p", "c", "o", "f", "g", "s")
TRAIT_KEYS = ("trait", "trait_name", "feature", "name", "label")
STATE_KEYS = ("state", "value", "majority_state", "majority")
DB_KEYS = ("database", "source", "provenance", "db")


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def find_latest_build_run(pipeline_dir: Path) -> Path:
    runs_dir = pipeline_dir / "runs"
    if not runs_dir.exists():
        raise FileNotFoundError(f"Missing runs directory: {runs_dir}")

    candidates = [
        p
        for p in runs_dir.glob("build_taxdb_*")
        if p.is_dir() and (p / "mags_kraken2").exists() and (p / "mags_input_kraken.csv").exists()
    ]
    if not candidates:
        raise FileNotFoundError(f"No run with mags_kraken2 and mags_input_kraken.csv found in {runs_dir}")

    return max(candidates, key=lambda p: p.stat().st_mtime)


def normalize_mag_id_from_fasta(filename: str) -> str:
    """
    Example:
      METAMDBG-MetaBAT2-so240416_duplex.1128.fa.fa -> METAMDBG-MetaBAT2-so240416_duplex.1128.fa
    """
    name = filename
    for ext in (".gz",):
        if name.endswith(ext):
            name = name[: -len(ext)]
    for ext in (".fa", ".fna", ".fasta"):
        if name.endswith(ext):
            # Remove one trailing FASTA extension.
            # Example: *.fa.fa -> *.fa
            return name[: -len(ext)]
    return name


def find_mag_fastas(run_dir: Path) -> List[Path]:
    mags_dir = run_dir / "mags_kraken2"
    fastas = sorted(
        [
            p
            for p in mags_dir.iterdir()
            if p.is_file() and p.name.endswith((".fa", ".fa.gz", ".fna", ".fna.gz", ".fasta", ".fasta.gz"))
        ]
    )
    return fastas


def parse_gtdb_taxonomy(taxonomy: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not isinstance(taxonomy, str):
        return out

    for part in taxonomy.split(";"):
        part = part.strip()
        if "__" not in part:
            continue
        prefix, value = part.split("__", 1)
        prefix = prefix.strip()
        value = value.strip()
        if prefix in RANK_PREFIXES:
            out[prefix] = value
    return out


def likely_non_empty_taxon(value: Optional[str]) -> bool:
    if value is None:
        return False
    value = value.strip()
    if not value:
        return False
    bad = {
        "",
        "sp",
        "sp.",
        "bacterium",
        "uncultured bacterium",
        "unclassified",
        "unknown",
    }
    if value.lower() in bad:
        return False
    if value in {"_", "NA", "nan", "None"}:
        return False
    return True


def build_taxon_name_candidates(row: pd.Series) -> List[str]:
    candidates: List[str] = []

    # 1) Parse deepest names from GTDB-like taxonomy strings.
    for col in ("closest_placement_taxonomy", "closest_genome_taxonomy", "classification", "pplacer_taxonomy"):
        tax = row.get(col)
        labels = parse_gtdb_taxonomy(tax)
        genus = labels.get("g")
        species = labels.get("s")
        family = labels.get("f")
        order = labels.get("o")
        class_name = labels.get("c")
        phylum = labels.get("p")

        if likely_non_empty_taxon(species):
            if likely_non_empty_taxon(genus) and not species.startswith(genus):
                candidates.append(f"{genus} {species}")
            candidates.append(species)
        if likely_non_empty_taxon(genus):
            candidates.append(genus)
        if likely_non_empty_taxon(family):
            candidates.append(family)
        if likely_non_empty_taxon(order):
            candidates.append(order)
        if likely_non_empty_taxon(class_name):
            candidates.append(class_name)
        if likely_non_empty_taxon(phylum):
            candidates.append(phylum)

    # 2) Deduplicate while preserving order.
    seen = set()
    deduped: List[str] = []
    for c in candidates:
        c = c.strip()
        if not c or c in seen:
            continue
        seen.add(c)
        deduped.append(c)

    return deduped


def extract_accession_from_row(row: pd.Series) -> Optional[str]:
    for col in ("closest_placement_reference", "closest_genome_reference", "other_related_references(genome_id,species_name,radius,ANI,AF)"):
        val = row.get(col)
        if not isinstance(val, str):
            continue
        m = ACCESSION_RE.search(val)
        if m:
            return m.group(0)
    return None


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    timeout: int = 60,
    verify_ssl: bool = True,
    max_retries: int = 3,
    pause_sec: int = 5,
) -> requests.Response:
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            if method == "GET":
                resp = session.get(url, params=params, timeout=timeout, verify=verify_ssl)
            elif method == "POST":
                resp = session.post(url, params=params, json=json_body, timeout=timeout, verify=verify_ssl)
            else:
                raise ValueError(f"Unsupported method: {method}")
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_retries:
                sleep_for = pause_sec * attempt
                log(f"Request failed ({method} {url}) attempt {attempt}/{max_retries}: {exc}; retrying in {sleep_for}s")
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Request failed after {max_retries} attempts: {method} {url} ({last_exc})")


def taxid_from_accession(
    accession: str,
    session: requests.Session,
    timeout: int,
    verify_ssl: bool,
    max_retries: int,
) -> Optional[int]:
    url = f"https://api.ncbi.nlm.nih.gov/datasets/v2alpha/genome/accession/{accession}/dataset_report"
    try:
        r = request_with_retry(
            session,
            "GET",
            url,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            pause_sec=3,
        )
    except Exception:
        return None

    if r.status_code != 200:
        return None

    try:
        payload = r.json()
    except Exception:
        return None

    reports = payload.get("reports")
    if not isinstance(reports, list) or not reports:
        return None

    org = reports[0].get("organism", {}) if isinstance(reports[0], dict) else {}
    taxid = org.get("tax_id")
    if isinstance(taxid, int):
        return taxid
    if isinstance(taxid, str) and taxid.isdigit():
        return int(taxid)
    return None


def taxid_from_ncbi_name(
    name: str,
    session: requests.Session,
    timeout: int,
    verify_ssl: bool,
    max_retries: int,
) -> Optional[int]:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "taxonomy",
        "term": f"{name}[Scientific Name]",
        "retmode": "json",
        "retmax": 1,
    }

    try:
        r = request_with_retry(
            session,
            "GET",
            url,
            params=params,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            pause_sec=2,
        )
    except Exception:
        return None

    if r.status_code != 200:
        return None

    try:
        payload = r.json()
    except Exception:
        return None

    ids = payload.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None

    first = str(ids[0])
    if first.isdigit():
        return int(first)
    return None


def first_scalar(dct: dict, keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        if key not in dct:
            continue
        value = dct[key]
        if isinstance(value, (str, int, float, bool)):
            return str(value)
    return None


def collect_trait_like_records(
    obj,
    *,
    taxid_hint: Optional[int] = None,
    path: str = "$",
    out: Optional[List[dict]] = None,
) -> List[dict]:
    if out is None:
        out = []

    if isinstance(obj, dict):
        local_taxid = taxid_hint
        for k in ("taxonomy_id", "taxid", "ncbi_taxonomy_id"):
            v = obj.get(k)
            if isinstance(v, int):
                local_taxid = v
            elif isinstance(v, str) and v.isdigit():
                local_taxid = int(v)

        trait_name = first_scalar(obj, TRAIT_KEYS)
        has_trait_hint = trait_name is not None or any(k in obj for k in ("trait", "trait_name", "feature"))

        if has_trait_hint:
            rec = {
                "taxonomy_id_in_record": local_taxid,
                "trait_name": trait_name,
                "trait_state": first_scalar(obj, STATE_KEYS),
                "database": first_scalar(obj, DB_KEYS),
                "json_path": path,
            }

            # Keep compact scalar fields for downstream inspection.
            for key, value in obj.items():
                if isinstance(value, (str, int, float, bool)):
                    rec[f"field_{key}"] = value
            out.append(rec)

        for key, value in obj.items():
            collect_trait_like_records(value, taxid_hint=local_taxid, path=f"{path}/{key}", out=out)

    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            collect_trait_like_records(value, taxid_hint=taxid_hint, path=f"{path}[{i}]", out=out)

    return out


def safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        fv = float(v)
    except Exception:
        return None
    if math.isnan(fv):
        return None
    return fv


def build_report_html(report_md: str, output_html: Path) -> None:
    escaped = (
        report_md.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    html = f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>MetaTraits MAG API Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; line-height: 1.45; }}
pre {{ background: #f7f7f7; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
</style>
</head>
<body>
<h1>MetaTraits MAG API Report</h1>
<pre>{escaped}</pre>
</body>
</html>
"""
    output_html.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Annotate MAGs against MetaTraits API and summarize traits.")
    parser.add_argument(
        "--pipeline-dir",
        type=Path,
        default=Path("/home/jbentes/projects/bioinformatics/nf_core_taxprofiler/custom_create_tax_db_for_MAGs/pipeline_build_taxdb"),
        help="Base directory containing runs/build_taxdb_*",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Specific build_taxdb run directory. If omitted, latest run is selected.",
    )
    parser.add_argument(
        "--bin-summary",
        type=Path,
        default=Path("/home/jbentes/projects/bioinformatics/nf_core_mag/long_only/nfcore-mag-hybrid-so240416-20260202_084826_from_DAVID/GenomeBinning/bin_summary.tsv"),
        help="nf-core/mag bin_summary.tsv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Default: <run-dir>/metatraits_api_<timestamp>",
    )
    parser.add_argument(
        "--metatraits-base-url",
        default="https://metatraits.embl.de/api/v1",
        help="MetaTraits API base URL",
    )
    parser.add_argument("--timeout-sec", type=int, default=90, help="HTTP request timeout (seconds)")
    parser.add_argument("--max-retries", type=int, default=3, help="Retry attempts for HTTP calls")
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="Verify SSL certificates (off by default to avoid cluster CA issues)",
    )
    args = parser.parse_args()

    if not args.verify_ssl and urllib3 is not None:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    pipeline_dir = args.pipeline_dir.resolve()
    run_dir = args.run_dir.resolve() if args.run_dir else find_latest_build_run(pipeline_dir)

    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    if not args.bin_summary.exists():
        raise FileNotFoundError(f"bin_summary TSV not found: {args.bin_summary}")

    out_dir = args.output_dir.resolve() if args.output_dir else run_dir / f"metatraits_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    raw_dir = out_dir / "raw_api"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    log(f"Run dir: {run_dir}")
    log(f"Output dir: {out_dir}")

    fasta_files = find_mag_fastas(run_dir)
    if not fasta_files:
        raise RuntimeError(f"No MAG FASTA files found in {run_dir / 'mags_kraken2'}")

    mag_ids = [normalize_mag_id_from_fasta(p.name) for p in fasta_files]
    log(f"Detected {len(mag_ids)} MAG FASTA files")

    bins = pd.read_csv(args.bin_summary, sep="\t")
    selected = bins[bins["bin"].astype(str).isin(set(mag_ids))].copy()
    log(f"Matched {len(selected)} rows in bin_summary.tsv")

    if len(selected) != len(mag_ids):
        missing = sorted(set(mag_ids) - set(selected["bin"].astype(str).tolist()))
        log(f"Warning: {len(missing)} MAGs were not found in bin_summary.tsv")

    depth_cols = [c for c in selected.columns if str(c).startswith("Depth ")]

    session = requests.Session()
    mapping_rows: List[dict] = []

    for _, row in selected.iterrows():
        mag = str(row["bin"])
        accession = extract_accession_from_row(row)
        ncbi_taxid = None
        taxid_source = None
        name_attempts: List[str] = []

        if accession:
            ncbi_taxid = taxid_from_accession(
                accession,
                session,
                timeout=args.timeout_sec,
                verify_ssl=args.verify_ssl,
                max_retries=args.max_retries,
            )
            if ncbi_taxid is not None:
                taxid_source = "ncbi_accession"

        if ncbi_taxid is None:
            for candidate in build_taxon_name_candidates(row):
                name_attempts.append(candidate)
                taxid_candidate = taxid_from_ncbi_name(
                    candidate,
                    session,
                    timeout=args.timeout_sec,
                    verify_ssl=args.verify_ssl,
                    max_retries=args.max_retries,
                )
                if taxid_candidate is not None:
                    ncbi_taxid = taxid_candidate
                    taxid_source = "ncbi_taxonomy_name"
                    break

        record = {
            "MAG": mag,
            "Name": row.get("Name"),
            "ncbi_taxid": ncbi_taxid,
            "taxid_source": taxid_source,
            "closest_accession": accession,
            "classification": row.get("classification"),
            "closest_placement_taxonomy": row.get("closest_placement_taxonomy"),
            "classification_method": row.get("classification_method"),
            "mapping_status": "mapped" if ncbi_taxid is not None else "unmapped",
            "name_candidates_tried": " | ".join(name_attempts[:10]),
        }
        for col in depth_cols:
            record[col] = row.get(col)
        mapping_rows.append(record)

    mapping_df = pd.DataFrame(mapping_rows)
    if mapping_df.empty:
        mapping_df = pd.DataFrame(
            columns=[
                "MAG",
                "Name",
                "ncbi_taxid",
                "taxid_source",
                "closest_accession",
                "classification",
                "closest_placement_taxonomy",
                "classification_method",
                "mapping_status",
                "name_candidates_tried",
            ]
            + depth_cols
        )
    else:
        mapping_df = mapping_df.sort_values(["mapping_status", "MAG"]).reset_index(drop=True)
    mapping_df.to_csv(out_dir / "mag_taxid_mapping.csv", index=False)

    mapped_taxids = sorted({int(x) for x in mapping_df["ncbi_taxid"].dropna().tolist()})
    mags_by_taxid: Dict[int, List[str]] = defaultdict(list)
    for _, row in mapping_df[mapping_df["mapping_status"] == "mapped"].iterrows():
        mags_by_taxid[int(row["ncbi_taxid"])].append(row["MAG"])

    log(f"Mapped MAGs: {len(mapping_df[mapping_df['mapping_status'] == 'mapped'])}/{len(mapping_df)}")
    log(f"Unique NCBI taxonomy IDs to query in MetaTraits: {len(mapped_taxids)}")

    api_status_rows: List[dict] = []
    trait_rows: List[dict] = []

    for idx, taxid in enumerate(mapped_taxids, start=1):
        url = f"{args.metatraits_base_url.rstrip('/')}/traits/taxonomy/{taxid}"
        log(f"MetaTraits [{idx}/{len(mapped_taxids)}]: taxonomy_id={taxid}")

        try:
            r = request_with_retry(
                session,
                "GET",
                url,
                timeout=args.timeout_sec,
                verify_ssl=args.verify_ssl,
                max_retries=args.max_retries,
                pause_sec=8,
            )
            status_code = r.status_code
            text_len = len(r.text)

            if status_code != 200:
                api_status_rows.append(
                    {
                        "taxonomy_id": taxid,
                        "api_status": "http_error",
                        "http_status": status_code,
                        "bytes": text_len,
                        "error": (r.text[:400] if r.text else ""),
                    }
                )
                continue

            payload = r.json()
            (raw_dir / f"{taxid}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            trait_like = collect_trait_like_records(payload, taxid_hint=taxid)
            for rec in trait_like:
                for mag in mags_by_taxid.get(taxid, []):
                    row = {
                        "MAG": mag,
                        "taxonomy_id": taxid,
                        "trait_name": rec.get("trait_name"),
                        "trait_state": rec.get("trait_state"),
                        "database": rec.get("database"),
                        "json_path": rec.get("json_path"),
                    }
                    for key, value in rec.items():
                        if key.startswith("field_"):
                            row[key] = value
                    trait_rows.append(row)

            api_status_rows.append(
                {
                    "taxonomy_id": taxid,
                    "api_status": "ok",
                    "http_status": status_code,
                    "bytes": text_len,
                    "n_trait_like_records": len(trait_like),
                    "n_mags": len(mags_by_taxid.get(taxid, [])),
                }
            )

        except Exception as exc:
            api_status_rows.append(
                {
                    "taxonomy_id": taxid,
                    "api_status": "request_failed",
                    "http_status": None,
                    "bytes": None,
                    "error": str(exc),
                }
            )

    api_status_df = pd.DataFrame(api_status_rows)
    if not api_status_df.empty:
        api_status_df = api_status_df.sort_values(["api_status", "taxonomy_id"]).reset_index(drop=True)
    api_status_df.to_csv(out_dir / "mag_api_status.csv", index=False)

    traits_df = pd.DataFrame(trait_rows)
    if traits_df.empty:
        traits_df = pd.DataFrame(columns=["MAG", "taxonomy_id", "trait_name", "trait_state", "database", "json_path"])
    traits_df.to_csv(out_dir / "mag_traits_long.csv", index=False)

    # Per-MAG summary.
    if len(traits_df) > 0:
        traits_norm = traits_df.copy()
        traits_norm["trait_name"] = traits_norm["trait_name"].fillna("").astype(str).str.strip()
        traits_norm = traits_norm[traits_norm["trait_name"] != ""]

        summary = (
            traits_norm.groupby("MAG", as_index=False)
            .agg(
                n_trait_rows=("trait_name", "size"),
                n_unique_traits=("trait_name", pd.Series.nunique),
            )
            .sort_values(["n_unique_traits", "n_trait_rows"], ascending=False)
        )
    else:
        summary = pd.DataFrame(columns=["MAG", "n_trait_rows", "n_unique_traits"])

    mag_summary = mapping_df[["MAG", "ncbi_taxid", "mapping_status"] + depth_cols].merge(summary, on="MAG", how="left")
    mag_summary = mag_summary.fillna({"n_trait_rows": 0, "n_unique_traits": 0})
    mag_summary["n_trait_rows"] = mag_summary["n_trait_rows"].astype(int)
    mag_summary["n_unique_traits"] = mag_summary["n_unique_traits"].astype(int)

    if not api_status_df.empty:
        status_map = api_status_df.set_index("taxonomy_id")["api_status"].to_dict()
        mag_summary["api_status"] = mag_summary["ncbi_taxid"].map(lambda t: status_map.get(int(t), "not_queried") if pd.notna(t) else "unmapped")
    else:
        mag_summary["api_status"] = mag_summary["ncbi_taxid"].map(lambda _: "not_queried")

    mag_summary.to_csv(out_dir / "mag_traits_summary.csv", index=False)

    # Trait expression over time (weighted by MAG depth columns).
    expr_rows: List[dict] = []
    if len(depth_cols) > 0 and len(traits_df) > 0:
        trait_presence = (
            traits_df[["MAG", "trait_name"]]
            .dropna(subset=["trait_name"])
            .assign(trait_name=lambda d: d["trait_name"].astype(str).str.strip())
        )
        trait_presence = trait_presence[trait_presence["trait_name"] != ""]
        trait_presence = trait_presence.drop_duplicates()

        depth_df = mapping_df[["MAG"] + depth_cols].copy()
        merged = trait_presence.merge(depth_df, on="MAG", how="left")

        for depth_col in depth_cols:
            for trait_name, grp in merged.groupby("trait_name"):
                vals = [safe_float(x) for x in grp[depth_col].tolist()]
                vals = [x for x in vals if x is not None]
                expr_rows.append(
                    {
                        "trait_name": trait_name,
                        "timepoint": depth_col.replace("Depth ", "", 1),
                        "expression_sum_depth": sum(vals) if vals else 0.0,
                        "mags_with_trait": int(grp["MAG"].nunique()),
                    }
                )

    expr_df = pd.DataFrame(expr_rows)
    if not expr_df.empty:
        expr_df = expr_df.sort_values(["timepoint", "expression_sum_depth"], ascending=[True, False]).reset_index(drop=True)
    else:
        expr_df = pd.DataFrame(columns=["trait_name", "timepoint", "expression_sum_depth", "mags_with_trait"])
    expr_df.to_csv(out_dir / "trait_expression_over_time.csv", index=False)

    n_total = len(mapping_df)
    n_mapped = int((mapping_df["mapping_status"] == "mapped").sum())
    n_api_ok = int((api_status_df["api_status"] == "ok").sum()) if not api_status_df.empty else 0
    n_api_fail = int((api_status_df["api_status"] != "ok").sum()) if not api_status_df.empty else 0
    n_trait_rows = len(traits_df)
    n_unique_traits = int(traits_df["trait_name"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique()) if len(traits_df) > 0 else 0

    lines = []
    lines.append("# MetaTraits MAG API Report")
    lines.append("")
    lines.append(f"- Date: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Run directory: {run_dir}")
    lines.append(f"- Output directory: {out_dir}")
    lines.append(f"- MAG FASTA files detected: {n_total}")
    lines.append(f"- MAGs mapped to NCBI taxonomy IDs: {n_mapped}")
    lines.append(f"- MetaTraits API OK responses: {n_api_ok}")
    lines.append(f"- MetaTraits API failed responses: {n_api_fail}")
    lines.append(f"- Trait rows extracted: {n_trait_rows}")
    lines.append(f"- Unique trait names extracted: {n_unique_traits}")
    lines.append("")

    if len(depth_cols) == 0:
        lines.append("- Temporal depth columns: none found in bin_summary.tsv")
    elif len(depth_cols) == 1:
        lines.append(f"- Temporal depth columns: only one timepoint found ({depth_cols[0]}), so temporal trend is limited.")
    else:
        lines.append(f"- Temporal depth columns: {', '.join(depth_cols)}")

    lines.append("")
    lines.append("## Output Files")
    lines.append("- mag_taxid_mapping.csv")
    lines.append("- mag_api_status.csv")
    lines.append("- mag_traits_long.csv")
    lines.append("- mag_traits_summary.csv")
    lines.append("- trait_expression_over_time.csv")
    lines.append("- raw_api/<taxonomy_id>.json")

    report_md = "\n".join(lines)
    (out_dir / "report.md").write_text(report_md, encoding="utf-8")
    build_report_html(report_md, out_dir / "report.html")

    log("Finished.")
    log(f"Report: {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
