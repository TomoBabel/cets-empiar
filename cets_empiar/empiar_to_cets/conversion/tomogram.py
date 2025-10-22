from cets_empiar.empiar_to_cets.utils.yaml_parsing import RegionDefinition
from cets_empiar.empiar_to_cets.utils.empiar_utils import EMPIARFileList, get_files_matching_pattern
from cets_empiar.empiar_to_cets.utils.metadata_utils import read_mrc_header
from cets_empiar.empiar_to_cets.conversion.coordinate_system import COORDINATE_SYSTEMS
from cets_empiar.empiar_to_cets.conversion.coordinate_transformation import make_coordinate_transformation


def create_cets_tomograms_from_region_definition(
        accession_id: str,
        region: RegionDefinition, 
        empiar_files: EMPIARFileList
) -> list[dict]:
    
    cets_tomograms = []
    accession_no = accession_id.split("-")[1]
    for tomogram in region.tomograms:
        tomogram_paths = get_files_matching_pattern(
            empiar_files, 
            tomogram.file_pattern
        )

        if not tomogram_paths:
            raise ValueError(f"No files found matching pattern: {tomogram.file_pattern}")

        # assuming one file per tomogram
        cets_tomogram_dict = {}
        if len(tomogram_paths) == 1:
            file_path = f"/empiar/world_availability/{accession_no}/data/{tomogram_paths[0]}"
            cets_tomogram_dict["path"] = f"https://ftp.ebi.ac.uk{file_path}"

            # assume mrc file
            mrc_header_info = read_mrc_header(file_path)

            cets_tomogram_dict["width"] = mrc_header_info["dimensions"][0]
            cets_tomogram_dict["height"] = mrc_header_info["dimensions"][1]
            cets_tomogram_dict["depth"] = mrc_header_info["dimensions"][2]

            # assume two coordinate systems
            cets_tomogram_dict["coordinate_systems"] = [
                COORDINATE_SYSTEMS["default_image_voxel"],
                COORDINATE_SYSTEMS["physical_sampling_angstrom"]
            ]

            coordinate_transformation = make_coordinate_transformation(
                type="scale", 
                input_cs="default_image_voxel", 
                output_cs = "physical_sampling_angstrom", 
                params=[mrc_header_info["pixel_size"]]
            )

            cets_tomogram_dict["coordinate_transformations"] = [coordinate_transformation]

            cets_tomograms.append(cets_tomogram_dict)
        
        else:
            raise ValueError(f"Multiple files found for tomogram pattern: {tomogram.file_pattern}")

    return cets_tomograms
