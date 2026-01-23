#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import json
import re
from typing import Dict, Iterable, Iterator, List, Tuple

import colrev.loader.load_utils as load_utils
import colrev.writer.write_utils as write_utils
from colrev.constants import RecordState


def yaml_escape(value: object) -> str:
    """Return a YAML-safe double-quoted scalar (content only)."""
    if value is None:
        return ""
    # json.dumps returns a valid JSON string literal with quotes around it.
    # YAML 1.2 accepts JSON-style escapes, so we can safely reuse it.
    return json.dumps(str(value), ensure_ascii=False)[1:-1]


def record_to_bibtex(rec: dict) -> str:
    """Reconstruct a BibTeX entry from a record dict."""
    entrytype = rec.get("ENTRYTYPE", "article")
    key = rec.get("ID") or rec.get("citation_key") or rec.get("colrev_id")

    if not key:
        raise ValueError("Record is missing a citation key (ID / citation_key / colrev_id).")

    field_lines: List[str] = []
    max_field_len = 10

    skip_fields = {
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
    }

    for field, value in rec.items():
        if field in skip_fields:
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

    # URL
    if rec.get("url"):
        lines.append(f"UR  - {rec['url']}")

    lines.append("ER  - ")
    return "\n".join(lines)


def _split_authors(author_field: str) -> List[str]:
    author_field = (author_field or "").strip()
    if not author_field:
        return []
    return [a.strip() for a in author_field.split(" and ") if a.strip()]


def _parse_person_name(author: str) -> Tuple[str, str]:
    """
    Return (family, given_names) for a single author.

    Handles:
    - "Family, Given Middle"
    - "Given Middle Family"
    """
    a = re.sub(r"\s+", " ", author.strip())
    if "," in a:
        family, given = [p.strip() for p in a.split(",", 1)]
        return family, given
    parts = a.split(" ")
    if len(parts) == 1:
        return parts[0], ""
    family = parts[-1]
    given = " ".join(parts[:-1])
    return family, given


def _given_to_initials(given: str) -> str:
    # keep hyphens in initials (e.g., Jean-Paul -> J.-P.)
    given = re.sub(r"\s+", " ", (given or "").strip())
    if not given:
        return ""
    chunks = given.split(" ")
    initials: List[str] = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if "-" in c:
            sub = [s for s in c.split("-") if s]
            initials.append("-".join([f"{s[0].upper()}." for s in sub]))
        else:
            initials.append(f"{c[0].upper()}.")
    return " ".join(initials)


def format_apa_authors(author_field: str) -> str:
    """
    APA-ish author formatting:
    - 1 author: Family, I.
    - 2 authors: Family, I., & Family, I.
    - 3+ authors: Family, I., Family, I., & Family, I.
    """
    authors = _split_authors(author_field)
    if not authors:
        return ""

    formatted: List[str] = []
    for a in authors:
        family, given = _parse_person_name(a)
        initials = _given_to_initials(given)
        if initials:
            formatted.append(f"{family}, {initials}")
        else:
            formatted.append(f"{family}")

    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def format_apa_reference(rec: dict) -> str:
    """
    Construct a single APA-ish reference (good-enough, not a full APA engine).

    Examples:
    - Journal article:
      Author, A. A. (2020). Title. Journal, 12(3), 1–10. https://doi.org/...
    - Conference paper:
      Author, A. A. (2020). Title. In Booktitle (pp. 1–10). https://doi.org/...
    """
    authors = format_apa_authors(str(rec.get("author", "")))
    year = str(rec.get("year", "")).strip()
    year_part = f"({year})." if year else "(n.d.)."

    title = str(rec.get("title", "")).strip().rstrip(".")
    title_part = f"{title}." if title else ""

    entrytype = str(rec.get("ENTRYTYPE", "article")).lower()

    journal = str(rec.get("journal", "")).strip()
    booktitle = str(rec.get("booktitle", "")).strip()
    volume = str(rec.get("volume", "")).strip()
    number = str(rec.get("number", "")).strip()
    pages = str(rec.get("pages", "")).strip()

    pages_part = ""
    if pages:
        pages_part = pages.replace("--", "–")  # en-dash

    outlet_part = ""
    if journal:
        vol_issue = ""
        if volume:
            vol_issue = volume
        if number:
            vol_issue = f"{vol_issue}({number})" if vol_issue else f"({number})"
        if vol_issue and pages_part:
            outlet_part = f"{journal}, {vol_issue}, {pages_part}."
        elif vol_issue:
            outlet_part = f"{journal}, {vol_issue}."
        elif pages_part:
            outlet_part = f"{journal}, {pages_part}."
        else:
            outlet_part = f"{journal}."
    elif booktitle:
        pp = ""
        if pages_part:
            pp = f"(pp. {pages_part})."
        outlet_part = f"In {booktitle} {pp}".strip()
        if not outlet_part.endswith("."):
            outlet_part += "."
    else:
        outlet_part = ""

    doi_raw = str(rec.get("doi", "")).strip()
    url_raw = str(rec.get("url", "")).strip()
    doi = ""
    if doi_raw:
        doi = doi_raw if doi_raw.startswith("http") else f"https://doi.org/{doi_raw}"

    link_part = doi or url_raw
    link_part = link_part.strip()
    if link_part and not link_part.endswith("."):
        link_part += "."

    parts = []
    if authors:
        parts.append(f"{authors} {year_part}")
    else:
        parts.append(f"{year_part}")
    if title_part:
        parts.append(title_part)
    if outlet_part:
        parts.append(outlet_part)
    if link_part:
        parts.append(link_part)

    return " ".join([p.strip() for p in parts if p.strip()])


def record_to_qmd_content(rec: dict, key: str, bibtex: str, ris: str, apa: str) -> str:
    """Create the .qmd file content for a single record."""
    title = yaml_escape(rec.get("title", ""))
    authors_raw = str(rec.get("author", "")).strip()
    author_list = [a.replace("{", "").replace("}", "").strip() for a in _split_authors(authors_raw)]
    year = str(rec.get("year", "")).strip()

    # DOI normalize
    doi_raw = str(rec.get("doi", "")).strip()
    doi = f"https://doi.org/{doi_raw}" if doi_raw and not doi_raw.startswith("http") else doi_raw

    url = str(rec.get("url", "")).strip()

    journal = yaml_escape(rec.get("journal", ""))
    outlet = rec.get("journal") or rec.get("booktitle") or ""

    try:
        cited_by = int(rec.get("cited_by", 0))
    except (TypeError, ValueError):
        cited_by = 0

    categories: List[str] = []
    if "lr_type_pare_et_al" in rec and rec["lr_type_pare_et_al"]:
        categories.append(str(rec["lr_type_pare_et_al"]))
    if "cited_by" in rec:
        try:
            if int(rec["cited_by"]) > 500:
                categories.append("highly-cited")
        except (TypeError, ValueError):
            pass

    author_yaml = "\n".join([f"  - {yaml_escape(a)}" for a in author_list]) if author_list else ""

    categories_yaml = "\n".join([f"  - {yaml_escape(c)}" for c in categories]) if categories else ""

    links_section = ""
    if doi or url:
        lines = ["", "## Links", ""]
        if doi:
            lines.append(f"- DOI: <{doi}>")
        if url:
            lines.append(f"- URL: <{url}>")
        links_section = "\n".join(lines) + "\n"

    qmd = f"""---
title: "{title}"
author:
{author_yaml if author_yaml else "  - \"\""}
topic: "{yaml_escape(rec.get('topic', ''))}"
categories:
{categories_yaml if categories_yaml else "  - \"\""}
date: "{yaml_escape(year)}"
doi: "{yaml_escape(doi)}"
url: "{yaml_escape(url)}"
journal:
  name: "{journal}"
cited_by: {cited_by}
outlet: "{yaml_escape(outlet)}"
---

## Citation: APA


::: {{.citebox}}
{apa}
:::

## Citation: BibTeX

```bibtex
{bibtex}
```

## Citation: RIS

```Markdown
{ris}
```
{links_section}"""
    return qmd


def iter_records(records) -> Iterator[Tuple[str, dict]]:
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
        if rec.get("colrev_status") != RecordState.rev_synthesized:
            continue

        rec.setdefault("ID", key)

        bibtex_entry = record_to_bibtex(rec)
        ris_entry = record_to_ris(rec)
        apa_ref = format_apa_reference(rec)

        qmd_content = record_to_qmd_content(rec, key=key, bibtex=bibtex_entry, ris=ris_entry, apa=apa_ref)

        qmd_path = out_dir / f"{key}.qmd"
        qmd_path.write_text(qmd_content, encoding="utf-8")

        count += 1
        print(f"Wrote {qmd_path}")

    print(f"Done. Wrote {count} records to {out_dir}")


def convert_to_csv() -> None:
    filename = Path("data/records.bib")
    records = load_utils.load(filename=filename)

    exclude: List[str] = []
    for record_dict in records.values():
        if record_dict.get("colrev_status") != RecordState.rev_synthesized:
            exclude.append(record_dict.get("ID"))

    for exclude_id in exclude:
        if exclude_id:
            records.pop(exclude_id, None)

    write_utils.write_file(records, filename=filename.with_suffix(".csv"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_qmd_from_bib.py records.bib [output_dir]")
        sys.exit(1)

    bib_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "papers"
    main(bib_file, out_dir)

    # Optional: also export synthesized records to CSV (expects data/records.bib)
    try:
        convert_to_csv()
    except FileNotFoundError:
        # ignore if the repo doesn't have data/records.bib
        pass
