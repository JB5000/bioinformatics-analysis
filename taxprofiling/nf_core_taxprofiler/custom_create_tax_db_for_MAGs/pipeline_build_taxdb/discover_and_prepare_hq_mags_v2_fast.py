"""
Prepare HQ MAG inputs for nf-core/createtaxdb.
Optimized version: builds FASTA index once to avoid repeated rglob() calls.
"""

import argparse
import csv
import gzip
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

SUMMARY_GLOBS = [
    "**/bin_summary*.tsv",
    "**/*bin*summary*.tsv",
    "**/*checkm*.tsv",
    "**/*quality*summary*.tsv",
]


def build_fasta_index(nfcore_mag_outdir: Path, cache_file: Optional[Path] = None) -> dict:
    """Build a fast index of all FASTA files using find command."""
    if cache_file and cache_file.exists():
        print(f"Loading FASTA index from cache: {cache_file}")
        with open(cache_file) as f:
            data = json.load(f)
        return {k: Path(v) for k, v in data.items()}

    print(f"Building FASTA index from {nfcore_mag_outdir}...", flush=True)
    index = {}

    try:
        # Include plain and gzipped FASTA files.
        cmd = [
            "find",
            str(nfcore_mag_outdir),
            "-type",
            "f",
            "(",
            "-name",
            "*.fa",
            "-o",
            "-name",
            "*.fna",
            "-o",
            "-name",
            "*.fasta",
            "-o",
            "-name",
            "*.fa.gz",
            "-o",
            "-name",
            "*.fna.gz",
            "-o",
            "-name",
            "*.fasta.gz",
            ")",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f"find failed with code {result.returncode}: {result.stderr.strip()}")

        count = 0
        for line in result.stdout.splitlines():
            if not line:
                continue
            p = Path(line)
            index[p.name] = p

            # Add key without extension; for .gz drop two suffixes.
            stem = p.stem
            if p.suffix == ".gz":
                stem = Path(stem).stem
            if stem not in index:
                index[stem] = p

            count += 1
            if count % 1000 == 0:
                print(f"  Indexed {count} files...", flush=True)

        print(f"Found {count} FASTA file paths in index", flush=True)

        # If `find` returns no files (or unexpectedly misses files), fallback to pathlib.
        if count == 0:
            print("FASTA index from find is empty; trying pathlib fallback...", flush=True)
            for pattern in ("*.fa", "*.fna", "*.fasta", "*.fa.gz", "*.fna.gz", "*.fasta.gz"):
                for p in nfcore_mag_outdir.rglob(pattern):
                    if not p.is_file():
                        continue
                    index[p.name] = p
                    stem = p.stem
                    if p.suffix == ".gz":
                        stem = Path(stem).stem
                    if stem not in index:
                        index[stem] = p
                    count += 1

            print(f"Fallback indexed {count} FASTA file paths", flush=True)

        if cache_file:
            print(f"Writing FASTA index cache to {cache_file}", flush=True)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump({k: str(v) for k, v in index.items()}, f)

        if not index:
            raise RuntimeError(
                f"No FASTA files found under {nfcore_mag_outdir}. Cannot prepare MAG DB inputs."
            )

        return index

    except (subprocess.TimeoutExpired, RuntimeError) as e:
        print(f"ERROR while indexing FASTA files: {e}", file=sys.stderr, flush=True)
        raise


def validate_nfcore_mag_outdir(path: Path) -> Path:
    path = path.resolve()
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")
    return path


def find_latest_summary(nfcore_mag_outdir: Path) -> Path:
    candidates = []
    for pattern in SUMMARY_GLOBS:
        candidates.extend(nfcore_mag_outdir.glob(pattern))
    candidates = [p for p in candidates if p.is_file()]

    if not candidates:
        raise FileNotFoundError(f"No summary TSV found in {nfcore_mag_outdir}")

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"Using summary: {latest.name}", flush=True)
    return latest


def locate_fasta(fasta_index: dict, mag_id: str) -> Optional[Path]:
    mag_id_clean = mag_id.strip()
    base_id = mag_id_clean

    for ext in (".fa", ".fna", ".fasta", ".fa.gz", ".fna.gz", ".fasta.gz"):
        if mag_id_clean.endswith(ext):
            base_id = mag_id_clean[: -len(ext)]
            break

    candidates = []
    for key in fasta_index:
        if key == mag_id_clean or key == base_id or key.startswith(base_id):
            candidates.append(fasta_index[key])

    if candidates:
        return sorted(candidates, key=lambda p: len(str(p)))[0]

    return None


def rewrite_fasta_with_taxid(input_fasta: Path, output_fasta: Path, taxid: int) -> list:
    accessions = []
    output_fasta.parent.mkdir(parents=True, exist_ok=True)

    opener = gzip.open if input_fasta.suffix == ".gz" else open
    with opener(input_fasta, "rt", encoding="utf-8", errors="ignore") as fin, output_fasta.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            if line.startswith(">"):
                header = line[1:].strip()
                if not header:
                    continue
                accession = header.split()[0]
                accessions.append(accession)
                fout.write(f">kraken:taxid|{taxid}|{header}\n")
            else:
                fout.write(line)

    return accessions


def main() -> int:
    p = argparse.ArgumentParser(description="Prepare HQ MAG inputs for nf-core/createtaxdb (fast)")
    p.add_argument("--nfcore-mag-outdir", type=Path, required=True)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--max-contamination", type=float, default=5.0)
    p.add_argument("--min-completeness", type=float, default=90.0)
    p.add_argument("--index-cache", type=Path, default=None)
    p.add_argument("--taxid-start", type=int, default=1000001)
    args = p.parse_args()

    nfcore_mag_outdir = validate_nfcore_mag_outdir(args.nfcore_mag_outdir)
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    cache_file = args.index_cache or run_dir.parent / ".fasta_index_cache.json"
    fasta_index = build_fasta_index(nfcore_mag_outdir, cache_file)

    summary_tsv = find_latest_summary(nfcore_mag_outdir)

    mags_hq = []
    with open(summary_tsv) as f:
        reader = csv.DictReader(f, delimiter="\t")
        raw_fields = list(reader.fieldnames or [])
        clean_fields = [fn.strip() for fn in raw_fields]
        fieldnames_lower = {fn.lower(): fn for fn in clean_fields if fn}

        id_col = fieldnames_lower.get("bin") or fieldnames_lower.get("id") or fieldnames_lower.get("name")
        if not id_col:
            id_col = next((fn for fn in clean_fields if fn), clean_fields[0])

        compl_col = fieldnames_lower.get("completeness") or clean_fields[-2]
        contam_col = fieldnames_lower.get("contamination") or clean_fields[-1]
        print(f"Columns: id={id_col}, completeness={compl_col}, contamination={contam_col}", flush=True)

        for row in reader:
            try:
                completeness = float(row.get(compl_col, 0) or 0)
                contamination = float(row.get(contam_col, 100) or 100)
                if completeness >= args.min_completeness and contamination <= args.max_contamination:
                    mag_id = row[id_col]
                    mags_hq.append({"id": mag_id, "completeness": completeness, "contamination": contamination})
            except (ValueError, KeyError):
                continue

    print(f"Selected {len(mags_hq)} HQ MAGs", flush=True)

    mags_input_csv = run_dir / "mags_input_kraken.csv"
    acc2tax_tsv = run_dir / "taxonomy_ficticia" / "acc2tax.tsv"
    nodes_dmp = run_dir / "taxonomy_ficticia" / "nodes.dmp"
    names_dmp = run_dir / "taxonomy_ficticia" / "names.dmp"
    mags_input_csv.parent.mkdir(parents=True, exist_ok=True)
    acc2tax_tsv.parent.mkdir(parents=True, exist_ok=True)

    written_taxids = []
    with open(mags_input_csv, "w") as csvf, open(acc2tax_tsv, "w") as acc2f:
        csv_writer = csv.writer(csvf)
        csv_writer.writerow(["id", "taxid", "fasta_dna", "fasta_aa"])
        acc2f_writer = csv.writer(acc2f, delimiter="\t")

        for idx, mag in enumerate(mags_hq, start=args.taxid_start):
            fasta_input = locate_fasta(fasta_index, mag["id"])
            if not fasta_input:
                print(f"WARNING: Could not find FASTA for {mag['id']}", file=sys.stderr, flush=True)
                continue

            fasta_output = run_dir / "mags_kraken2" / f"{mag['id']}.fa"
            accessions = rewrite_fasta_with_taxid(fasta_input, fasta_output, idx)
            if not accessions:
                print(f"WARNING: No FASTA entries found for {mag['id']} from {fasta_input}", file=sys.stderr, flush=True)
                continue

            csv_writer.writerow([mag["id"], idx, str(fasta_output), ""])
            mag_name = f"MAG_{mag['id']}"
            for acc in accessions:
                acc2f_writer.writerow([acc, idx, mag_name])
            written_taxids.append(idx)

    with open(nodes_dmp, "w") as f:
        f.write("1\t|\t1\t|\tno rank\t|\t\t|\t0\t|\t0\t|\t11\t|\t0\t|\t0\t|\t0\t|\t0\t|\n")
        for idx in written_taxids:
            f.write(f"{idx}\t|\t1\t|\tspecies\t|\t\t|\t0\t|\t0\t|\t11\t|\t0\t|\t0\t|\t0\t|\t0\t|\n")

    with open(names_dmp, "w") as f:
        f.write("1\t|\troot\t|\t\t|\tscientific name\t|\n")
        for idx in written_taxids:
            f.write(f"{idx}\t|\tMAG_{idx}\t|\t\t|\tscientific name\t|\n")

    if not written_taxids:
        print("ERROR: No MAG FASTA files were prepared. Cannot build a custom DB.", file=sys.stderr, flush=True)
        return 2

    print(f"Prepared {len(written_taxids)} MAG FASTA files for createTaxDB", flush=True)
    print(f"✓ Success - Generated all outputs in {run_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
