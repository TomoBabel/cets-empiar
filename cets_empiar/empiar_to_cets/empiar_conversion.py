import logging
from cets_data_model.models.models import Dataset

from cets_empiar.cets_utils import dict_to_cets_model, save_cets_model_to_json
from cets_empiar.empiar_to_cets.utils.yaml_parsing import load_empiar_yaml, parse_regions, RegionDefinition
from cets_empiar.empiar_to_cets.utils.empiar_utils import get_files_for_empiar_entry_cached, EMPIARFileList
from cets_empiar.empiar_to_cets.utils.metadata_utils import load_mdoc_file, load_xf_file
from cets_empiar.empiar_to_cets.conversion import (
    movie_stack_collection, 
    tilt_series, 
    alignment, 
    tomogram, 
    annotation
)


logger = logging.getLogger(__name__)


def convert_empiar_entry_to_cets_dataset(
        accession_id: str
):
    
    empiar_files = get_files_for_empiar_entry_cached(accession_id)

    yaml_definition_dict = load_empiar_yaml(accession_id)
    regions = parse_regions(yaml_definition_dict)

    cets_dataset_dict = {}
    dataset_regions = []
    for region in regions:
        cets_region_dict = populate_cets_region(
            accession_id,
            region, 
            empiar_files
        )
        dataset_regions.append(cets_region_dict)

    cets_dataset_dict["name"] = accession_id
    cets_dataset_dict["regions"] = dataset_regions
    cets_dataset = dict_to_cets_model(
        cets_dataset_dict, 
        cets_model_class=Dataset
    )
    save_cets_model_to_json(accession_id, accession_id, cets_dataset)


def populate_cets_region(
        accession_id: str, 
        region: RegionDefinition, 
        empiar_files: EMPIARFileList
) -> dict:
    
    cets_region = {}

    movie_metadata = None
    if region.movie_metadata:
        movie_metadata = load_mdoc_file(
            accession_id, 
            region.movie_metadata.file_pattern, 
            region.movie_metadata.label
        )
    
    if region.movie_stacks:
        cets_movie_stack_collection = movie_stack_collection.create_cets_movie_stack_collection_from_region_definition(
            accession_id, 
            region, 
            empiar_files, 
            movie_metadata
        )
        cets_region["movie_stack_collections"] = cets_movie_stack_collection
    
    if region.tilt_series_metadata:
        tilt_series_metadata = load_mdoc_file(
            accession_id, 
            region.tilt_series_metadata.file_pattern, 
            region.tilt_series_metadata.label
        )

    if region.tilt_series:
        cets_tilt_series = tilt_series.create_cets_tilt_series_from_region_definition(
            accession_id, 
            region, 
            empiar_files, 
            tilt_series_metadata)
        cets_region["tilt_series"] = cets_tilt_series

    if region.alignments:
        alignment_metadata = load_xf_file(
            accession_id, 
            region.alignments.file_pattern, 
            region.alignments.label
        )
        cets_alignments = alignment.create_cets_alignment_from_alignment_metadata(alignment_metadata)
        cets_region["alignments"] = cets_alignments
    
    cets_tomograms = None
    if region.tomograms:
        cets_tomograms = tomogram.create_cets_tomograms_from_region_definition(
            accession_id, 
            region, 
            empiar_files
        )
        cets_region["tomograms"] = cets_tomograms
    
    if region.annotations:
        cets_annotations = annotation.create_cets_annotations_from_region_definition(
            accession_id, 
            region, 
            cets_tomograms
        )
        cets_region["annotations"] = cets_annotations

    return cets_region
