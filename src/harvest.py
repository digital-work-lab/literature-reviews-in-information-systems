from colrev.env.local_index import LocalIndex
from pathlib import Path
import colrev.review_manager
import colrev.ops.check
from colrev.constants import Fields
import colrev.loader.load_utils
import colrev.writer.write_utils
from bib_dedupe.lookup import get_ids
from bib_dedupe.bib_dedupe import prep, block, match
import pandas as pd
import colrev.env.tei_parser
import typing
import colrev.record.record_id_setter
from colrev.constants import IDPattern

# TODO: maybe use curation wrapper + search-query (e.g., default record-status: md_prepared? + journals...)

# selected_curations = ["international-conference-on-information-systems", "european-journal-of-information-systems", "information-systems-journal", "information-systems-research", "journal-of-information-technology", "journal-of-management-information-systems", "journal-of-the-association-for-information-systems", "mis-quarterly", "the-journal-of-strategic-information-systems", "european-conference-on-information-systems", "americas-conference-on-information-systems", "communications-of-the-association-for-information-systems", "hawaii-international-conference-on-system-sciences", "pacific-asia-conference-on-information-systems", "decision-support-systems", "information-and-management", "information-systems-frontiers", "journal-of-information-systems-education"]
# selected_curations = ["european-journal-of-information-systems", "information-systems-journal", "information-systems-research", "journal-of-information-technology", "journal-of-management-information-systems", "journal-of-the-association-for-information-systems", "mis-quarterly", "the-journal-of-strategic-information-systems", "communications-of-the-association-for-information-systems", "decision-support-systems", "information-and-management", "information-systems-frontiers"]
selected_curations = ["communications-of-the-association-for-information-systems"]

KEYWORDS = ["literature review", "meta-analyis", "umbrella review", "narrative review", "descriptive review", "scoping review", "theoretical review", "realist review", "systematic review", "meta-analysis", "meta analysis", "meta-ethnography", "meta-synthesis"]

LR_REFS = [{'author': 'Wagner, G. and Lukyanenko, R. and Paré, G.', 'title': 'Artificial intelligence and the conduct of literature reviews', 'year': '2022', 'pages': '209--226', 'ENTRYTYPE': 'article', 'journal': 'Journal of Information Technology', 'volume': '37', 'number': '2'},
                       {"author": "Webster, Jane and Watson, Richard T.",
                        "journal": "MIS Quarterly",
                        "title": "Analyzing the Past to Prepare for the Future - Writing a Literature Review",
                        "year": "2002",
                        "volume": "26",
                        "number": "2",
                        "pages": "xiii--xxiii",
                        "ENTRYTYPE": "article"
                        }, {"doi": "10.1016/J.IM.2014.08.008",
                        "author": "Paré, Guy and Trudel, Marie-Claude and Jaana, Mirou and Kitsiou, Spyros",
                        "journal": "Information & Management",
                        "title": "Synthesizing information systems knowledge - A typology of literature reviews",
                        "year": "2015",
                        "volume": "52",
                        "number": "2",
                        "pages": "183--199",
                        "ENTRYTYPE": "article"
                        }
]

harvested_records = []
filename = "/home/gerit/ownCloud/data/literature_reviews/LRDatabase/literature-reviews-in-information-systems/data/records.bib"

id_setter = colrev.record.record_id_setter.IDSetter(
    id_pattern=IDPattern.three_authors_year,
    skip_local_index=False,
)

def import_lrs_from_curation():
    # Initialize the LocalIndex from the default location (usually in the CoLRev environment)
    local_index = LocalIndex()
    records_lr_is = colrev.loader.load_utils.load(filename=filename)

    # Iterate over all curation records
    for curation in local_index.get_curations():
        
        # print(str(curation))
        if not any(str(curation).endswith(str(x)) for x in selected_curations):
            continue
        # Each curation has a 'file' attribute pointing to its path
        print(curation)

        review_manager = colrev.review_manager.ReviewManager(path_str=curation)
        colrev.ops.check.CheckOperation(review_manager)
        records = review_manager.dataset.load_records_dict()

        for record_dict in records.values():
            if Fields.YEAR not in record_dict:
                continue
            if not record_dict[Fields.YEAR].isdigit():
                continue
            if int(record_dict[Fields.YEAR]) < 2010:
                continue
            # print(record_dict["ID"])

            title_and_abstract = record_dict.get(Fields.TITLE, "") + " " + record_dict.get(Fields.ABSTRACT, "")
            title_and_abstract = title_and_abstract.lower()

            ref_match = False
            if "file" in record_dict:
                pdf_file = Path(curation) / record_dict["file"]
                try:
                    tei_object = colrev.env.tei_parser.TEIParser(pdf_path=pdf_file)
                    ref_match = matches_reference(tei_object,LR_REFS)
                except:
                    pass

            if ref_match or any(x in title_and_abstract for x in KEYWORDS):

                # Use bib-dedupe to check if an equivalent record already exists
                duplicate_ids = get_ids(
                    records=records_lr_is,
                    record_dict=record_dict,
                    # optionally:
                    # include_maybe=False,
                    # verbosity_level=None,
                    # cpu=-1,
                )

                if duplicate_ids:
                    # We’ve found at least one existing LR record that bib-dedupe
                    # considers a duplicate of this one – skip it.
                    print(
                        f"Skipping {record_dict[Fields.ID]} "
                        f"(duplicate of {', '.join(map(str, duplicate_ids))})"
                    )
                    continue

                # print(record_dict[Fields.ID])
                # harvested_records.append(record_dict)
                if record_dict[Fields.ID] in records_lr_is:
                    print(f"Skipping {record_dict[Fields.ID]}")
                    continue
                print(f'Import {record_dict[Fields.ID]}')
                record_dict["colrev_status"] = "md_processed"
                record_dict.pop("colrev_origin", None)
                record_dict.pop("colrev_masterdata_provenance", None)
                record_dict.pop("colrev_data_provenance", None)
                records_lr_is[record_dict[Fields.ID]] = record_dict

    # for harvested_record in harvested_records:

    # print()
    colrev.writer.write_utils.write_file(records_lr_is, filename=filename)


def import_lrs_from_pdfs():

    records_lr_is = colrev.loader.load_utils.load(filename=filename)

    PDF_PATH=Path("/home/gerit/.colrev/curated_metadata/international-conference-on-information-systems/data/pdfs/2025")
    

    for pdf_file in PDF_PATH.rglob("*.pdf"):  # includes subdirs

        print(pdf_file)
        # if "Trustworthy AI to conduct literature review" not in str(pdf_file):
        #     continue

        title_and_abstract = record_dict.get(Fields.TITLE, "") + " " + record_dict.get(Fields.ABSTRACT, "")
        title_and_abstract = title_and_abstract.lower()

        # TODO: could check local-index for tei (for efficiency)
        tei_object = colrev.env.tei_parser.TEIParser(pdf_path=pdf_file)

        if matches_reference(tei_object,LR_REFS) or any(x in title_and_abstract for x in KEYWORDS):

            record_dict = tei_object.get_metadata()

            # Use bib-dedupe to check if an equivalent record already exists
            duplicate_ids = get_ids(
                records=records_lr_is,
                record_dict=record_dict,
                # optionally:
                # include_maybe=False,
                # verbosity_level=None,
                # cpu=-1,
            )

            if duplicate_ids:
                # We’ve found at least one existing LR record that bib-dedupe
                # considers a duplicate of this one – skip it.
                print(
                    f"Skipping {record_dict[Fields.ID]} "
                    f"(duplicate of {', '.join(map(str, duplicate_ids))})"
                )
                continue
            # print(record_dict[Fields.ID])
            # harvested_records.append(record_dict)

            # print(f'Import {record_dict[Fields.ID]}')
            records_lr_is["TEMP_HARVEST_ID"] = record_dict
            records_lr_is = id_setter.set_ids(
                records=records_lr_is,
                selected_ids=["TEMP_HARVEST_ID"],
            )

    # for harvested_record in harvested_records:

    # print()
    colrev.writer.write_utils.write_file(records_lr_is, filename=filename)

def check_duplicates():
    records_lr_is = colrev.loader.load_utils.load(filename=filename)
    records_df = pd.DataFrame.from_dict(records_lr_is, orient="index")
    records_df = prep(records_df)

    # 2. Blocking
    blocked_df = block(records_df)

    # 3. Matching
    matched_df = match(blocked_df)

    duplicate_pairs = (
        matched_df
        .loc[matched_df["duplicate_label"] == "duplicate", ["ID_1", "ID_2"]]
    )
    print(duplicate_pairs)

def matches_reference(tei_object, references: typing.List[dict]) -> bool:
    pdf_references_list = tei_object.get_references()
    pdf_references = {r["tei_id"]: r for r in pdf_references_list}
    # print(pdf_references)
    for record_dict in references:
        duplicate_ids = get_ids(
            records=pdf_references,
            record_dict=record_dict,
        )
        if duplicate_ids:
            print(f"Found {record_dict}")
            return True

    # print(references)
    return False

if __name__ == "__main__":
    import_lrs_from_curation()

    # Rationale: do not iterate over PDFs directly because at some point, relevant records need to be prepared (linked to pdf records)
    # import_lrs_from_pdfs()
    # check_duplicates()
