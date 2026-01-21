import cets_data_model.models.models as cets_models
import logging

from cets_empiar.empiar_to_cets.conversion.entity_conversion import (
    tilt_series_and_movie, 
    tomogram
)
from cets_empiar.empiar_to_cets.parsing import metadata_parsing, yaml_parsing
from cets_empiar.empiar_to_cets.utils import empiar_utils


logger = logging.getLogger(__name__)


def create_cets_region(
    accession_id: str, 
    region: yaml_parsing.RegionDefinition, 
    empiar_files: empiar_utils.EMPIARFileList, 
    metadata_file: metadata_parsing.MdocFile | None
) -> cets_models.Region:

    cets_movie_stack_collection, cets_tilt_series = tilt_series_and_movie.create_cets_tilt_and_movie_families(
        accession_id, 
        region, 
        empiar_files, 
        metadata_file
    )

    cets_tomogram = tomogram.create_cets_tomogram(
        accession_id, 
        region, 
        empiar_files, 
        cets_tilt_series.id
    )

    cets_region = cets_models.Region.model_construct(
        id=region.name, 
        movie_stack_collection=cets_movie_stack_collection, 
        tilt_series=[cets_tilt_series], 
        tomograms=[cets_tomogram]
    )

    return cets_region
