import cets_data_model.models.models as cets_models
import logging
from pathlib import Path

from cets_empiar.empiar_to_cets.parsing import yaml_parsing
from cets_empiar.empiar_to_cets.utils import empiar_utils
from cets_empiar.empiar_to_cets.utils.metadata_utils import read_mrc_header
from cets_empiar.empiar_to_cets.conversion.entity_conversion.coordinate_system import COORDINATE_SYSTEMS
from cets_empiar.empiar_to_cets.conversion.entity_conversion.coordinate_transformation import make_coordinate_transformation


logger = logging.getLogger(__name__)


def create_cets_tomogram(
    accession_id: str, 
    region: yaml_parsing.RegionDefinition, 
    empiar_files: empiar_utils.EMPIARFileList, 
    tilt_series_id: str
) -> cets_models.Tomogram:
    
    accession_no = accession_id.split("-")[1]

    tomogram_paths = empiar_utils.get_files_matching_pattern(
        empiar_files, 
        region.tomogram_file_pattern
    )

    if len(tomogram_paths) == 1:
        empiar_path = f"/empiar/world_availability/{accession_no}/data/{tomogram_paths[0]}"
        
        file_extension = Path(empiar_path).suffix.lstrip('.')
        if file_extension != "mrc":
            logger.info(f"Cannot extract some tomogram metadata as file is {file_extension}, not mrc.")
            tomogram_width = None
            tomogram_height = None
            tomogram_depth = None

            # TODO: how to handle coordinate systems and transformations in this case?
            coordinate_systems = []
            coordinate_transformation = None
        else:
            mrc_header_info = read_mrc_header(empiar_path)

            tomogram_width = mrc_header_info["dimensions"][0]
            tomogram_height = mrc_header_info["dimensions"][1]
            tomogram_depth = mrc_header_info["dimensions"][2]

            # assume two coordinate systems
            coordinate_systems = [
                COORDINATE_SYSTEMS["default_image_voxel"],
                COORDINATE_SYSTEMS["physical_sampling_angstrom"]
            ]

            coordinate_transformation = make_coordinate_transformation(
                type="scale", 
                input_cs="default_image_voxel", 
                output_cs = "physical_sampling_angstrom", 
                params=[mrc_header_info["pixel_size"]]
            )
    else:
        raise ValueError(f"Multiple files found for tomogram pattern: {region.tomogram_file_pattern}")

    tomogram_id = f"{region.name}_tomogram"
    cets_tomogram = cets_models.Tomogram.model_construct(
        id=tomogram_id, 
        path=f"https://ftp.ebi.ac.uk{empiar_path}", 
        tilt_series_id=tilt_series_id, 
        width=tomogram_width, 
        height=tomogram_height, 
        depth=tomogram_depth, 
        coordinate_systems=coordinate_systems, 
        coordinate_transformations=[coordinate_transformation] if coordinate_transformation else []
    )

    return cets_tomogram
