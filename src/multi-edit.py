
import colrev.loader.load_utils
import colrev.writer.write_utils
import colrev.record.record_id_setter
from colrev.constants import IDPattern


filename = "/home/gerit/ownCloud/data/literature_reviews/LRDatabase/literature-reviews-in-information-systems/data/records.bib"

id_setter = colrev.record.record_id_setter.IDSetter(
    id_pattern=IDPattern.three_authors_year,
    skip_local_index=False,
)

records_lr_is = colrev.loader.load_utils.load(filename=filename)

# for record_dict in records_lr_is.values():
#     record_dict.pop("colrev_origin", None)
#     record_dict.pop("colrev_masterdata_provenance", None)
#     record_dict.pop("colrev_data_provenance", None)
#     record_dict["colrev_status"] = "md_prepared"


# selected_ids = []
# for record_dict in records_lr_is.values():
#     if record_dict["ENTRYTYPE"] != "misc":
#         continue
    
#     record_dict["booktitle"] = "inproceedings"
#     record_dict["booktitle"] = "International Conference on Information Systems"
#     record_dict["year"] = "2025"
#     selected_ids.append(record_dict["ID"])

# records_lr_is = id_setter.set_ids(
#     records=records_lr_is,
#     selected_ids=["TEMP_HARVEST_ID"],
# )

# for record_dict in records_lr_is.values():
#     if record_dict.get("colrev_status", "") == "md_needs_manual_preparation":
#         record_dict["colrev_status"] = "md_prepared"

colrev.writer.write_utils.write_file(records_lr_is, filename=filename)
