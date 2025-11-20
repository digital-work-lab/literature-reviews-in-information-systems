#!/usr/bin/env python3
from pathlib import Path
import sys

import colrev.loader.load_utils as load_utils


def yaml_escape(value: str) -> str:
    """Escape double quotes for safe inclusion in YAML."""
    if value is None:
        return ""
    return str(value).replace('"', '\\"')


def record_to_bibtex(rec: dict) -> str:
    """Reconstruct a BibTeX entry from a record dict."""
    entrytype = rec.get("ENTRYTYPE", "article")
    key = rec.get("ID") or rec.get("citation_key") or rec.get("colrev_id")

    if not key:
        raise ValueError("Record is missing a citation key (ID / citation_key / colrev_id).")

    field_lines = []
    # max_field_len = max(len(field) for field in rec.keys())
    max_field_len = 10
    for field, value in rec.items():
        if field in {"ENTRYTYPE", "ID", "citation_key", "colrev_id", "colrev_origin", "colrev_status", "colrev_masterdata_provenance", "colrev_data_provenance", "colrev.dblp.dblp_key", "curation_id", "language", "note", "topic", "lr_type_pare_et_al", "goal_rowe", "synthesis", "r_gaps", "theory_building", "aggregating_evidence", "r_agenda", "r_agenda_levels", "cited_by"}:
            continue
        if value is None or value == "":
            continue

        v = str(value).replace("\n", " ").strip()
        field_lines.append(f"  {field:<{max_field_len}} = {{{v}}},")

    if field_lines:
        field_lines[-1] = field_lines[-1].rstrip(",")

    lines = [f"@{entrytype}{{{key},"] + field_lines + ["}"]
    return "\n".join(lines)


def record_to_qmd_content(rec: dict) -> str:
    """Create the .qmd file content for a single record."""
    title = yaml_escape(rec.get("title", ""))
    authors = yaml_escape(rec.get("author", ""))
    author_list = authors.split(' and ')
    author_str = '- ' + '\n- '.join(author_list)

    topic = ""
    year = str(rec.get("year", "")).strip()

    doi_raw = str(rec.get("doi", "")).strip()
    if doi_raw and not doi_raw.startswith("http"):
        doi = f"https://doi.org/{doi_raw}"
    else:
        doi = doi_raw

    journal = yaml_escape(rec.get("journal", ""))

    try:
        cited_by = int(rec.get("cited_by", 0))
    except (TypeError, ValueError):
        cited_by = 0

    bibtex = record_to_bibtex(rec)
    outlet = rec.get("journal", rec.get("booktitle", ""))

    categories = []
    # if "goal_rowe" in rec:
    #     categories += [rec["goal_rowe"]]
    if "lr_type_pare_et_al" in rec:
        categories += [rec["lr_type_pare_et_al"]]
    if "cited_by" in rec and int(rec["cited_by"]) > 500:
        categories += ["highly-cited"]

    qmd = f"""---
title: "{title}"
author:
{author_str}
topic: "{yaml_escape(topic)}"
categories: {categories}
date: "{year}"
doi: "{yaml_escape(doi)}"
journal:
  name: "{journal}"
cited_by: {cited_by}
outlet: "{outlet}"
---

Citation:

```bibtex
{bibtex}
```
"""
    return qmd


def iter_records(records):
    """Yield (key, record) pairs from whatever load() returns."""
    if isinstance(records, dict):
        if "records" in records and isinstance(records["records"], dict):
            for k, v in records["records"].items():
                yield k, v
        else:
            for k, v in records.items():
                if isinstance(v, dict):
                    yield k, v
    elif isinstance(records, list):
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                continue
            key = rec.get("ID") or rec.get("citation_key") or rec.get("colrev_id") or f"rec{idx+1}"
            yield key, rec
    else:
        raise TypeError(f"Unsupported records type: {type(records)}")


def main(bib_filename: str, output_dir: str = "papers") -> None:
    bib_path = Path(bib_filename)
    if not bib_path.is_file():
        raise FileNotFoundError(f"BibTeX file not found: {bib_path}")

    print(f"Loading records from {bib_path}...")
    records = load_utils.load(filename=bib_path)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for key, rec in iter_records(records):
        rec = dict(rec)
        rec.setdefault("ID", key)

        qmd_content = record_to_qmd_content(rec)
        out_path = out_dir / f"{key}.qmd"

        out_path.write_text(qmd_content, encoding="utf-8")
        count += 1
        print(f"Wrote {out_path}")

    print(f"Done. Wrote {count} .qmd files to {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_qmd_from_bib.py records.bib [output_dir]")
        sys.exit(1)

    bib_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "papers"
    main(bib_file, out_dir)
