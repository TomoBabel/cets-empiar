import cets_data_model.models.models as cets_models
import logging

from cets_empiar.empiar_to_cets.parsing import metadata_parsing, yaml_parsing
from cets_empiar.empiar_to_cets.utils import empiar_utils


logger = logging.getLogger(__name__)


def create_cets_tilt_and_movie_families(
    accession_id: str, 
    region: dict, 
    empiar_files: empiar_utils.EMPIARFileList, 
    metadata: metadata_parsing.MdocFile | None
) -> tuple[cets_models.MovieStackCollection, cets_models.TiltSeries]:

    if metadata is None:
        cets_movie_stack_collection, cets_tilt_series = create_cets_tilt_and_movie_families_without_metadata(
            accession_id, 
            region, 
            empiar_files
        )
    else:
        cets_movie_stack_collection, cets_tilt_series = create_cets_tilt_and_movie_families_with_metadata(
            accession_id, 
            region, 
            empiar_files, 
            metadata
        )

    return cets_movie_stack_collection, cets_tilt_series


def create_cets_tilt_and_movie_families_without_metadata(
    accession_id: str, 
    region: yaml_parsing.RegionDefinition, 
    empiar_files: empiar_utils.EMPIARFileList
) -> tuple[cets_models.MovieStackCollection, cets_models.TiltSeries]:
    """
    Create minimal CETS MovieStackCollection and TiltSeries objects without metadata.
    
    Args:
        accession_id (str): EMPIAR accession ID
        region (yaml_parsing.RegionDefinition): Region definition from YAML
        empiar_files (empiar_utils.EMPIARFileList): List of EMPIAR files for the entry
    
    Returns:
        tuple[cets_models.MovieStackCollection, cets_models.TiltSeries]:
            The created MovieStackCollection and TiltSeries CETS objects with minimal information.
    """
    accession_no = accession_id.split("-")[1]
    
    tilt_series_paths = empiar_utils.get_files_matching_pattern(
        empiar_files, 
        region.tilt_series_file_pattern
    )
    is_single_stack_file = len(tilt_series_paths) == 1
    
    movie_stack_paths = []
    if region.movie_stack_file_pattern:
        try:
            movie_stack_paths = empiar_utils.get_files_matching_pattern(
                empiar_files, 
                region.movie_stack_file_pattern
            )
        except ValueError:
            logger.warning(f"No movie stack files found for pattern: {region.movie_stack_file_pattern}")
    
    movie_stacks = []
    for idx, movie_stack_path in enumerate(movie_stack_paths):
        movie_stack_id = f"{region.name}_movie_stack_{idx:03d}"
        movie_stack_url = f"{empiar_utils.EMPIAR_BASE_URL}{accession_no}/data/{movie_stack_path}"
        
        movie_stack = cets_models.MovieStack.model_construct(
            id=movie_stack_id,
            path=movie_stack_url,
            images=[]
        )
        movie_stacks.append(movie_stack)
    
    movie_stack_collection = _create_movie_stack_collection(
        region_name=region.name,
        movie_stacks=movie_stacks
    )
    
    # Create minimal tilt series with empty images list
    tilt_series = _create_tilt_series(
        region_name=region.name,
        accession_no=accession_no,
        tilt_series_paths=tilt_series_paths,
        is_single_stack_file=is_single_stack_file, 
        images=[]
    )
    
    return movie_stack_collection, tilt_series


def create_cets_tilt_and_movie_families_with_metadata(
    accession_id: str, 
    region: yaml_parsing.RegionDefinition, 
    empiar_files: empiar_utils.EMPIARFileList, 
    metadata: metadata_parsing.MdocFile
) -> tuple[cets_models.MovieStackCollection, cets_models.TiltSeries]:
    """
    Create CETS MovieStackCollection and TiltSeries objects, with subclasses, 
    with the aid of mdoc metadata file.

    Args:
        accession_id (str): EMPIAR accession ID
        region (yaml_parsing.RegionDefinition): Region definition from YAML
        empiar_files (empiar_utils.EMPIARFileList): List of EMPIAR files for the entry
        metadata (metadata_parsing.MdocFile): Parsed mdoc metadata file
    
    Returns:
        tuple[cets_models.MovieStackCollection, cets_models.TiltSeries]:
            The created MovieStackCollection and TiltSeries CETS objects.
    """
    accession_no = accession_id.split("-")[1]
    
    # TODO: use pixel_spacing for coordinate system/transformation
    pixel_spacing = _extract_pixel_spacing(metadata)
    
    tilt_series_paths = empiar_utils.get_files_matching_pattern(
        empiar_files, 
        region.tilt_series_file_pattern
    )
    is_single_stack_file = len(tilt_series_paths) == 1
    
    movie_stacks, tilt_images = _create_movie_stacks_and_tilt_images(
        metadata=metadata,
        region=region, 
        accession_no=accession_no,
        empiar_files=empiar_files,
        is_single_stack_file=is_single_stack_file,
        tilt_series_paths=tilt_series_paths
    )
    
    movie_stack_collection = _create_movie_stack_collection(
        region_name=region.name,
        movie_stacks=movie_stacks
    )
    
    tilt_series = _create_tilt_series(
        region_name=region.name,
        accession_no=accession_no,
        tilt_series_paths=tilt_series_paths,
        is_single_stack_file=is_single_stack_file, 
        images=tilt_images
    )
    
    return movie_stack_collection, tilt_series


def _extract_pixel_spacing(metadata: metadata_parsing.MdocFile) -> float | None:
    """Extract and validate pixel spacing from metadata."""
    pixel_spacing = metadata.global_headers.get("PixelSpacing")
    if pixel_spacing:
        try:
            return float(pixel_spacing)
        except (ValueError, TypeError):
            logger.info(f"Could not parse pixel size from metadata: {pixel_spacing}")
            return None
    else:
        logger.info("Pixel spacing not found in metadata.")
        return None


def _extract_image_dimensions(metadata: metadata_parsing.MdocFile) -> list[int] | None:
    """Extract and validate image dimensions from metadata."""
    image_dimensions = metadata.global_headers.get("ImageSize")
    if image_dimensions:
        try:
            return [int(x) for x in image_dimensions.split()]
        except ValueError:
            logger.info(f"Could not parse image dimensions from metadata: {image_dimensions}")
            return None
    else:
        logger.info("Image dimensions not found in metadata.")
        return None


def _create_movie_stacks_and_tilt_images(
    metadata: metadata_parsing.MdocFile,
    region: yaml_parsing.RegionDefinition,
    accession_no: str,
    empiar_files: empiar_utils.EMPIARFileList,
    is_single_stack_file: bool,
    tilt_series_paths: list[str]
) -> tuple[list[cets_models.MovieStack], list[cets_models.TiltImage]]:
    """Process all z-sections to create corresponding movie frames, movie stacks, and tilt images."""
    movie_stacks = []
    tilt_images = []
    
    image_dimensions = _extract_image_dimensions(metadata)

    for z_section in metadata.z_sections:
        movie_stack = _create_movie_stack_for_section(
            z_section=z_section, 
            region=region, 
            accession_no=accession_no, 
            image_dimensions=image_dimensions, 
            empiar_files=empiar_files, 
        )
        movie_stacks.append(movie_stack)
        
        tilt_image = _create_tilt_image_for_section(
            z_section=z_section, 
            region=region, 
            accession_no=accession_no, 
            movie_stack_id=movie_stack.id, 
            image_dimensions=image_dimensions, 
            is_single_stack_file=is_single_stack_file, 
            tilt_series_paths=tilt_series_paths, 
            empiar_files=empiar_files
        )
        tilt_images.append(tilt_image)
    
    return movie_stacks, tilt_images


def _create_movie_stack_for_section(
    z_section: metadata_parsing.ZValueSection, 
    region: yaml_parsing.RegionDefinition, 
    accession_no: str, 
    image_dimensions: list[int] | None, 
    empiar_files: empiar_utils.EMPIARFileList, 
) -> cets_models.MovieStack:
    """Create a MovieStack object for a single z-section."""
    acquisition_metadata = metadata_parsing.parse_acquisition_metadata(z_section)
    
    movie_frames = _create_movie_frames(
        z_section=z_section,
        acquisition_metadata=acquisition_metadata,
        image_dimensions=image_dimensions
    )
    
    # TODO: this ties in a particular z-section with an empiar file, 
    # but if it fails, could fall back to matching pattern with files (as in no-metadata route), 
    # and assume correspondence with z-sections?
    subframe_path = z_section.metadata.get("SubFramePath")
    z_section_empiar_path, _ = metadata_parsing.match_mdoc_path_to_empiar(
        subframe_path, 
        region.movie_stack_filter_pattern, 
        region.movie_stack_file_pattern, 
        empiar_files, 
    )
    movie_stack_path = f"{empiar_utils.EMPIAR_BASE_URL}{accession_no}/data/{z_section_empiar_path}"
    
    movie_stack_id = f"{region.name}_movie_stack_{z_section.z_value:03d}"
    
    return cets_models.MovieStack.model_construct(
        id=movie_stack_id, 
        path=movie_stack_path, 
        images=movie_frames
    )


def _calculate_movie_frame_accumulated_dose(
    z_section: metadata_parsing.ZValueSection,
    frame_index: int
) -> float:
    """Calculate accumulated dose up to and including a specific frame."""    
    metadata = z_section.metadata
    
    # Dose accumulated before this tilt angle started
    # (includes any scout/focus images taken before the series)
    prior_dose = float(metadata["PriorRecordDose"])
    
    # Dose per frame
    frame_dose_str = metadata["FrameDosesAndNumber"].split()[0]
    dose_per_frame = float(frame_dose_str)
    
    # Accumulated dose up to and including this frame
    accumulated_dose = prior_dose + (dose_per_frame * (frame_index + 1))
    
    return accumulated_dose


def _create_movie_frames(
    z_section: metadata_parsing.ZValueSection, 
    acquisition_metadata: metadata_parsing.AcquisitionMetadata, 
    image_dimensions: list[int] | None
) -> list[cets_models.MovieFrame]:
    """Create MovieFrame objects for all frames in a movie stack."""
    num_frames = z_section.metadata.get("NumSubFrames", 0)
    movie_frames = []
    
    for f in range(num_frames):
        movie_frame_section = f
        
        accumulated_dose = _calculate_movie_frame_accumulated_dose(z_section, f)

        # TODO: allow for individual frame paths if available
        movie_frame = cets_models.MovieFrame.model_construct(
            section=movie_frame_section, 
            nominal_tilt_angle=acquisition_metadata.tilt_angle, 
            accumulated_dose=accumulated_dose, 
            width=image_dimensions[0] if image_dimensions else None, 
            height=image_dimensions[1] if image_dimensions else None
        )
        movie_frames.append(movie_frame)
    
    return movie_frames


def _calculate_tilt_image_accumulated_dose(
    z_section: metadata_parsing.ZValueSection
) -> float:
    """Calculate accumulated dose for a tilt image."""    
    metadata = z_section.metadata
    
    # Dose accumulated before this tilt angle started
    # (includes any scout/focus images taken before the series)
    prior_dose = float(metadata["PriorRecordDose"])
    
    frame_doses_and_number = metadata["FrameDosesAndNumber"].split()
    dose_per_frame = float(frame_doses_and_number[0])
    num_frames = int(frame_doses_and_number[1])
    
    # Accumulated dose up to and including this image
    accumulated_dose = prior_dose + (dose_per_frame * num_frames)
    
    return accumulated_dose


def _create_tilt_image_for_section(
    z_section: metadata_parsing.ZValueSection, 
    region: yaml_parsing.RegionDefinition, 
    accession_no: str, 
    movie_stack_id: str, 
    image_dimensions: list[int] | None, 
    is_single_stack_file: bool, 
    tilt_series_paths: list[str], 
    empiar_files: empiar_utils.EMPIARFileList
) -> cets_models.TiltImage:
    """Create a TiltImage object for a single z-section."""
    acquisition_metadata = metadata_parsing.parse_acquisition_metadata(z_section)
    
    if is_single_stack_file:
        tilt_image_path = None
    else:
        tilt_image_path = _resolve_tilt_image_path(
            z_section=z_section,
            region=region,
            accession_no=accession_no,
            tilt_series_paths=tilt_series_paths,
            empiar_files=empiar_files
        )
    
    section_index = z_section.z_value

    accumulated_dose = _calculate_tilt_image_accumulated_dose(z_section)
    
    return cets_models.TiltImage.model_construct(
        movie_stack_id=movie_stack_id, 
        path=tilt_image_path, 
        section=section_index, 
        nominal_tilt_angle=acquisition_metadata.tilt_angle, 
        accumulated_dose=accumulated_dose, 
        width=image_dimensions[0] if image_dimensions else None, 
        height=image_dimensions[1] if image_dimensions else None
    )


def _resolve_tilt_image_path(
    z_section, 
    region: yaml_parsing.RegionDefinition, 
    accession_no: str, 
    tilt_series_paths: list[str], 
    empiar_files: empiar_utils.EMPIARFileList
) -> str:
    """Resolve the tilt image path for multi-file tilt series."""
    subframe_path = z_section.metadata.get("SubFramePath")
    _, matched_file_parts = metadata_parsing.match_mdoc_path_to_empiar(
        subframe_path, 
        region.movie_stack_filter_pattern, 
        region.movie_stack_file_pattern, 
        empiar_files, 
    )
    
    expected_tilt_image_path = region.tilt_series_file_pattern.format(*matched_file_parts)
    
    if expected_tilt_image_path not in tilt_series_paths:
        raise ValueError(f"No tilt image file found at expected path '{expected_tilt_image_path}'")
    
    return f"{empiar_utils.EMPIAR_BASE_URL}{accession_no}/data/{expected_tilt_image_path}"


def _create_movie_stack_collection(
    region_name: str, 
    movie_stacks: list[cets_models.MovieStack]
) -> cets_models.MovieStackCollection:
    """Wrap movie stacks in a MovieStackCollection structure."""
    movie_stack_series_id = f"{region_name}_movie_stack_series"
    
    movie_stack_series = cets_models.MovieStackSeries.model_construct(
        id=movie_stack_series_id, 
        stacks=movie_stacks
    )
    
    return cets_models.MovieStackCollection.model_construct(
        movie_stacks=[movie_stack_series]
    )


def _create_tilt_series(
    region_name: str, 
    accession_no: str, 
    tilt_series_paths: list[str], 
    is_single_stack_file: bool, 
    images: list[cets_models.TiltImage]
) -> cets_models.TiltSeries:
    """Create the main TiltSeries object with tilt images and appropriate path."""
    tilt_series_id = f"{region_name}_tilt_series"
    movie_stack_series_id = f"{region_name}_movie_stack_series"
    
    if is_single_stack_file:
        tilt_series_path = f"{empiar_utils.EMPIAR_BASE_URL}{accession_no}/data/{tilt_series_paths[0]}"
    else:
        tilt_series_path = None
    
    return cets_models.TiltSeries.model_construct(
        id=tilt_series_id, 
        path=tilt_series_path, 
        images=images, 
        movie_stack_series_id=movie_stack_series_id
    )
