import cets_data_model.models.models as cets_models
import logging
from pathlib import Path

from cets_empiar.cets_utils import dict_to_cets_model, save_cets_model_to_json
from cets_empiar.empiar_to_cets.parsing import yaml_parsing
from cets_empiar.empiar_to_cets.utils import empiar_utils
from cets_empiar.empiar_to_cets.utils import metadata_utils
from cets_empiar.empiar_to_cets.conversion.entity_conversion import region


logger = logging.getLogger(__name__)


def convert_empiar_entry_to_cets(
    definition_path: Path
):
    """
    Convert an EMPIAR entry to CETS data.
    
    Args:
        definition_path: Path to the definition YAML file for the EMPIAR entry.
        process_mode: Whether STANDARD or WITH_MDOC, depending on whether mdoc files are available.
    """

    yaml_definition_dict, accession_id = yaml_parsing.load_empiar_definition_yaml(definition_path)
    region_definitions = yaml_parsing.parse_regions(yaml_definition_dict)

    empiar_files = empiar_utils.get_files_for_empiar_entry_cached(accession_id)

    cets_regions = []
    for region_definition in region_definitions:

        if region_definition.metadata_file is not None:
            metadata_file_label = f"{region_definition.name}_metadata_file"

            metadata_file = metadata_utils.load_mdoc_file(
                accession_id, 
                region_definition.metadata_file, 
                metadata_file_label
            )

        cets_region = region.create_cets_region(
            accession_id, 
            region_definition, 
            empiar_files, 
            metadata_file
        )

        cets_regions.append(cets_region)

    cets_dataset = cets_models.Dataset.model_construct(
        name=accession_id, 
        regions=cets_regions
    )
    cets_dataset = cets_models.Dataset.model_validate(cets_dataset.model_dump())
    save_cets_model_to_json(accession_id, cets_dataset)




#     if region.alignments:
#         alignment_metadata = load_xf_file(
#             accession_id, 
#             region.alignments.file_pattern, 
#             region.alignments.label
#         )
#         cets_alignments = alignment.create_cets_alignment_from_alignment_metadata(alignment_metadata)
#         cets_region["alignments"] = cets_alignments

    
#     if region.annotations:
#         cets_annotations = annotation.create_cets_annotations_from_region_definition(
#             accession_id, 
#             region, 
#             cets_tomograms
#         )
#         cets_region["annotations"] = cets_annotations

#     return cets_region
