import cets_data_model.models.models as cets_models
import logging
from pathlib import Path

from cets_empiar.cets_utils import save_cets_model_to_json
from cets_empiar.empiar_to_cets.parsing import yaml_parsing
from cets_empiar.empiar_to_cets.utils import empiar_utils
from cets_empiar.empiar_to_cets.utils import metadata_utils
from cets_empiar.empiar_to_cets.conversion.entity_conversion import region


logger = logging.getLogger(__name__)


def convert_empiar_entry_to_cets(
    definition_path: Path, 
    cets_output_dir: Path
):
    """
    Convert an EMPIAR entry to CETS data.
    
    Args:
        definition_path: Path to the definition YAML file for the EMPIAR entry.
        cets_output_dir: Path to CETS output json file.
    """

    yaml_definition_dict, accession_id = yaml_parsing.load_empiar_definition_yaml(definition_path)
    region_definitions = yaml_parsing.parse_regions(yaml_definition_dict)

    empiar_files = empiar_utils.get_files_for_empiar_entry_cached(accession_id)

    cets_regions = []
    for region_definition in region_definitions:
        
        metadata_file = None
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
    save_cets_model_to_json(accession_id, cets_dataset, cets_output_dir)
