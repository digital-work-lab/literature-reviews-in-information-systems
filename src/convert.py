#!/usr/bin/env python3
from pathlib import Path
import sys

import colrev.loader.load_utils as load_utils
from colrev.constants import RecordState
import colrev.loader.load_utils
import colrev.writer.write_utils

def yaml_escape(value: str) -> str:
    """Escape double quotes for safe inclusion in YAML."""
    if value is None:
        return ""
    return str(value).replace('"', '\"')


def record_to_bibtex(rec: dict) -> str:
    """Reconstruct a BibTeX entry from a record dict."""
    entrytype = rec.get("ENTRYTYPE", "article")
    key = rec.get("ID") or rec.get("citation_key") or rec.get("colrev_id")

    if not key:
        raise ValueError("Record is missing a citation key (ID / citation_key / colrev_id).")

    field_lines = []
    max_field_len = 10
    for field, value in rec.items():
        if field in {
            "ENTRYTYPE",
            "ID",
            "citation_key",
            "colrev_id",
            "colrev_origin",
            "colrev_status",
            "colrev_masterdata_provenance",
            "colrev_data_provenance",
            "colrev.dblp.dblp_key",
            "curation_id",
            "language",
            "note",
            "topic",
            "lr_type_pare_et_al",
            "goal_rowe",
            "synthesis",
            "r_gaps",
            "theory_building",
            "aggregating_evidence",
            "r_agenda",
            "r_agenda_levels",
            "cited_by",
        }:
            continue
        if value is None or value == "":
            continue

        v = str(value).replace("\n", " ").strip()
        field_lines.append(f"  {field:<{max_field_len}} = {{{v}}},")

    if field_lines:
        field_lines[-1] = field_lines[-1].rstrip(",")

    lines = [f"@{entrytype}{{{key},"] + field_lines + ["}"]
    return "\n".join(lines)


def record_to_ris(rec: dict) -> str:
    """Convert a record dict to a single RIS entry."""
    entrytype = str(rec.get("ENTRYTYPE", "article")).lower()
    type_map = {
        "article": "JOUR",
        "inproceedings": "CONF",
        "proceedings": "CONF",
        "conference": "CONF",
        "book": "BOOK",
        "phdthesis": "THES",
        "mastersthesis": "THES",
        "techreport": "RPRT",
    }
    ris_type = type_map.get(entrytype, "GEN")

    lines = [f"TY  - {ris_type}"]

    # Authors
    authors = str(rec.get("author", "")).strip()
    if authors:
        for a in authors.split(" and "):
            a = a.strip()
            if a:
                lines.append(f"AU  - {a}")

    # Title
    if rec.get("title"):
        lines.append(f"TI  - {rec['title']}")

    # Journal / booktitle
    outlet = rec.get("journal") or rec.get("booktitle")
    if outlet:
        lines.append(f"T2  - {outlet}")

    # Year
    year = str(rec.get("year", "")).strip()
    if year:
        lines.append(f"PY  - {year}")

    # Volume / issue / pages
    if rec.get("volume"):
        lines.append(f"VL  - {rec['volume']}")
    if rec.get("number"):
        lines.append(f"IS  - {rec['number']}")
    if rec.get("pages"):
        # crude split "start--end"
        pages = str(rec["pages"])
        if "--" in pages:
            sp, ep = pages.split("--", 1)
            lines.append(f"SP  - {sp.strip()}")
            lines.append(f"EP  - {ep.strip()}")
        else:
            lines.append(f"SP  - {pages.strip()}")

    # DOI
    if rec.get("doi"):
        lines.append(f"DO  - {rec['doi']}")

    # URL (if present)
    if rec.get("url"):
        lines.append(f"UR  - {rec['url']}")

    # End of record
    lines.append("ER  - ")
    return "\n".join(lines)


def record_to_qmd_content(rec: dict, key: str, bibtex: str, ris: str) -> str:
    """Create the .qmd file content for a single record."""
    title = yaml_escape(rec.get("title", ""))
    authors = yaml_escape(rec.get("author", ""))
    author_list = [a.replace("{", "").replace("}", "") for a in authors.split(" and ") if a]
    author_str = ""
    if author_list:
        author_str = "- " + "\n- ".join(author_list)

    topic = ""
    year = str(rec.get("year", "")).strip()

    # DOI (normalize to URL-style if needed)
    doi_raw = str(rec.get("doi", "")).strip()
    if doi_raw and not doi_raw.startswith("http"):
        doi = f"https://doi.org/{doi_raw}"
    else:
        doi = doi_raw

    # URL (publisher / landing page)
    url_raw = str(rec.get("url", "")).strip()
    url = url_raw

    journal = yaml_escape(rec.get("journal", ""))

    try:
        cited_by = int(rec.get("cited_by", 0))
    except (TypeError, ValueError):
        cited_by = 0

    outlet = rec.get("journal", rec.get("booktitle", ""))

    categories = []
    if "lr_type_pare_et_al" in rec:
        categories.append(rec["lr_type_pare_et_al"])
    if "cited_by" in rec:
        try:
            if int(rec["cited_by"]) > 500:
                categories.append("highly-cited")
        except (TypeError, ValueError):
            pass

    # Build optional links section for the markdown body
    links_section = ""
    if doi or url:
        lines = ["", "## Links", ""]
        if doi:
            lines.append(f"- DOI: <{doi}>")
        if url:
            lines.append(f"- URL: <{url}>")
        links_section = "\n".join(lines) + "\n"

    # Quarto YAML with code-copy enabled so code blocks have copy buttons
    qmd = f'''---
title: "{title}"
author:
{author_str}
topic: "{yaml_escape(topic)}"
categories: {categories}
date: "{year}"
doi: "{yaml_escape(doi)}"
url: "{yaml_escape(url)}"
journal:
  name: "{journal}"
cited_by: {cited_by}
outlet: "{outlet}"
---

## Citation: BibTeX

```bibtex
{bibtex}
```

## Citation: RIS

```bibtex
{ris}
```{links_section}'''
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
        if rec["colrev_status"] != RecordState.rev_synthesized:
            continue

        rec.setdefault("ID", key)

        # Per-record BibTeX and RIS (only embedded into QMD, no separate files)
        bibtex_entry = record_to_bibtex(rec)
        ris_entry = record_to_ris(rec)

        # .qmd with BibTeX block, RIS block, and DOI/URL links
        qmd_content = record_to_qmd_content(rec, key=key, bibtex=bibtex_entry, ris=ris_entry)

        qmd_path = out_dir / f"{key}.qmd"
        qmd_path.write_text(qmd_content, encoding="utf-8")


        count += 1
        print(f"Wrote {qmd_path}")

    print(f"Done. Wrote {count} records to {out_dir}")


def convert_to_csv() -> None:

    filename = Path("/home/gerit/ownCloud/data/literature_reviews/LRDatabase/literature-reviews-in-information-systems/data/records.bib")

    records = colrev.loader.load_utils.load(filename=filename)

    exclude = []
    for record_dict in records.values():
        if record_dict["colrev_status"] != RecordState.rev_synthesized:
            exclude.append(record_dict["ID"])
    
    for exclude_id in exclude:
        records.pop(exclude_id, None)

    colrev.writer.write_utils.write_file(records, filename=filename.with_suffix(".csv"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_qmd_from_bib.py records.bib [output_dir]")
        sys.exit(1)

    bib_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "papers"
    main(bib_file, out_dir)

    convert_to_csv()
