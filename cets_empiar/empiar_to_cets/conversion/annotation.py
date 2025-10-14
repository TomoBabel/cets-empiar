import logging
import numpy as np

from cets_empiar.empiar_to_cets.conversion.coordinate_system import COORDINATE_SYSTEMS
from cets_empiar.empiar_to_cets.conversion.coordinate_transformation import make_coordinate_transformation
from cets_empiar.empiar_to_cets.utils.annotation_utils import load_and_filter_annotation_star_file, get_coordinates_and_units_from_star_json
from cets_empiar.empiar_to_cets.utils.yaml_parsing import RegionDefinition


logger = logging.getLogger(__name__)


def create_new_annotation_coordinate_system_and_transformations(
    tomogram_transformations: list[dict] | None, 
    pixel_size: tuple[float, float, float] | None, 
    annotation_default_coordinate_system: str | None
) -> tuple[list[dict], list[dict]]:
    """
    Priority order:
    1. If annotation_default_coordinate_system is provided, use it directly
    2. If pixel_size is provided, create physical sampling coordinate system
    3. Otherwise, return empty lists
    
    Args:
        tomogram_transformations: Existing tomogram coordinate transformations
        pixel_size: Physical pixel size in angstroms (x, y, z)
        annotation_default_coordinate_system: Name of predefined coordinate system, set in definition file
        
    Returns:
        Tuple of (coordinate_systems, coordinate_transformations)
    """
    
    if annotation_default_coordinate_system:
        if annotation_default_coordinate_system not in COORDINATE_SYSTEMS:
            raise ValueError(f"Annotation default coordinate system {annotation_default_coordinate_system} not recognized.")
        
        return [COORDINATE_SYSTEMS[annotation_default_coordinate_system]], []
          
    if pixel_size:
        annotation_coordinate_systems = [COORDINATE_SYSTEMS["physical_sampling_angstrom"]]

        if matching_transform := next((tt for tt in (tomogram_transformations or []) if tt.get("output") == "physical_sampling_angstrom"), None):
            if np.allclose(matching_transform["scale"], pixel_size, atol=0.01):                
                return annotation_coordinate_systems, [matching_transform]

            
        annotation_coordinate_transformations = [
            make_coordinate_transformation(
                "scale", 
                "default_image_voxel", 
                "physical_sampling_angstrom", 
                [pixel_size]
            )
        ]

        return annotation_coordinate_systems, annotation_coordinate_transformations

    return [], []


def create_cets_annotations_from_region_definition(
        accession_id: str, 
        region: RegionDefinition, 
        cets_tomograms: list[dict]
) -> list[dict]:
    
    cets_annotations = []
    for annotation in region.annotations:
        for tomogram in cets_tomograms:

            if annotation.annotation_type == "point_set_3D":

                annotation_json_path = load_and_filter_annotation_star_file(
                    accession_id, 
                    annotation.label, 
                    annotation.file_name, 
                    image_name=annotation.image_name, 
                    tomogram_column=annotation.tomogram_column
                )

                # TODO: specify a manual override for pixel units, and check here.
                # And a flag if coordinates are known to be expressed in voxels. 
                annotation_origin_3d, pixel_size = get_coordinates_and_units_from_star_json(annotation_json_path)
                
                tomogram_coordinate_systems = tomogram.get("coordinate_systems", None)
                tomogram_transformations = tomogram.get("coordinate_transformations", None)
                if tomogram_coordinate_systems is None:
                    raise ValueError("A tomogram must have at least one coordinate system")
                
                # TODO: handle dealing with more than a scale transformation?
                annotation_coordinate_systems, annotation_coordinate_transforms = create_new_annotation_coordinate_system_and_transformations(
                    tomogram_transformations, 
                    pixel_size, 
                    annotation.default_coordinate_system
                )

                cets_annotation_dict = {
                    "origin3D": annotation_origin_3d, 
                    "coordinate_systems": annotation_coordinate_systems, 
                    "coordinate_transformations": annotation_coordinate_transforms, 
                    "path": annotation_json_path, 
                    "type": "point_set_3D"
                }

            cets_annotations.append(cets_annotation_dict)
    
    return cets_annotations
