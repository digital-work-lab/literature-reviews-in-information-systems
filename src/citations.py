#!/usr/bin/env python3
"""Enrich records.bib with Crossref citation counts.

- Loads records.bib with colrev
- For each record that has a DOI, queries Crossref
- Adds/updates a 'cited_by' field with the Crossref is-referenced-by-count
- Writes back to records.bib

Adjust the output field name ('cited_by') if you prefer a different name
(e.g., 'nr_citations').
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import colrev.loader.load_utils
import colrev.writer.write_utils
import colrev.env.environment_manager

# This imports the Endpoint class from your uploaded crossref_api.py
from colrev.packages.crossref.src.crossref_api import Endpoint


CITATION_FIELD = "cited_by"  # change to "nr_citations" or similar if preferred


def normalize_doi(doi: str) -> str:
    """Normalize DOI to bare form (no URL prefix, no 'doi:' prefix)."""
    doi = doi.strip()
    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
        "DOI:",
        "doi.org/",
        "dx.doi.org/",
    )
    for p in prefixes:
        if doi.lower().startswith(p.lower()):
            return doi[len(p) :].strip()
    return doi


def get_crossref_citation_count(doi: str) -> Optional[int]:
    """Return Crossref 'is-referenced-by-count' (cited-by) for a DOI, or None."""
    if not doi:
        return None

    doi = normalize_doi(doi)

    # Get email from git config the same way crossref_api does
    _, email = colrev.env.environment_manager.EnvironmentManager.get_name_mail_from_git()

    # Endpoint.__iter__ for /works/{doi} returns the 'message' dict from Crossref
    endpoint = Endpoint(f"https://api.crossref.org/works/{doi}", email=email)

    try:
        message = next(iter(endpoint))  # type: ignore[assignment]
    except StopIteration:
        return None
    except Exception as exc:  # network issues, etc.
        print(f"Warning: error querying Crossref for DOI {doi}: {exc}")
        return None

    if not isinstance(message, dict):
        return None

    count = message.get("is-referenced-by-count")
    if isinstance(count, int):
        return count

    # Sometimes it might come through as a string, be conservative:
    try:
        return int(count)
    except Exception:
        return None


def main() -> None:
    filename = Path("records.bib")

    if not filename.is_file():
        raise SystemExit(f"File not found: {filename}")

    print(f"Loading records from {filename} ...")
    records = colrev.loader.load_utils.load(filename=filename)

    updated = 0
    skipped_no_doi = 0
    skipped_no_count = 0

    for rec_id, rec in records.items():
        doi = rec.get("doi") or rec.get("DOI")
        if not doi:
            skipped_no_doi += 1
            continue

        print(f"Querying Crossref for {rec_id} (DOI: {doi}) ...")
        cited_by = get_crossref_citation_count(doi)
        if cited_by is None:
            print(f"  -> no citation count available")
            skipped_no_count += 1
            continue

        # Add/overwrite the citation field
        rec[CITATION_FIELD] = str(cited_by)
        updated += 1
        print(f"  -> {CITATION_FIELD} = {cited_by}")

    print(
        f"\nDone querying Crossref.\n"
        f"  Updated records with citation counts: {updated}\n"
        f"  Records without DOI: {skipped_no_doi}\n"
        f"  Records with DOI but no count: {skipped_no_count}\n"
    )

    print(f"Writing updated records back to {filename} ...")
    colrev.writer.write_utils.write_file(records, filename=filename)
    print("Finished.")


if __name__ == "__main__":
    main()
