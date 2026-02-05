import logging
import parse
import re
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field

from cets_empiar.empiar_to_cets.utils import empiar_utils

logger = logging.getLogger(__name__)


class ZValueSection(BaseModel):
    """
    Represents a single [ZValue = n] section from an .mdoc file.
    """

    z_value: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class MdocFile(BaseModel):
    """
    Represents a parsed .mdoc file with global headers and ZValue sections.
    """

    filename: str
    global_headers: dict[str, Any] = Field(default_factory=dict)
    z_sections: list[ZValueSection] = Field(default_factory=list)

    def search_by_subframe_path(
            self, 
            search_string: str, 
            case_sensitive: bool = False
        ) -> List[ZValueSection]:
        """
        Search for sections where the SubFramePath ends with the given search string.
        To be used to find the Z-section for a specific cryoET movie.
        
        Args:
            search_string: String to match against the end of SubFramePath
            case_sensitive: Whether to perform case-sensitive matching
            
        Returns:
            List (but should be one?) of ZValueSection objects that match the criteria
        """

        matches = []
        if self.z_sections:
            for section in self.z_sections:
                subframe_path = section.metadata.get("SubFramePath", None)
                if not subframe_path:
                    continue
                    
                subframe_path = str(subframe_path)
                
                if not case_sensitive:
                    subframe_path = subframe_path.lower()
                    search_string = search_string.lower()
                
                if subframe_path.endswith(search_string):
                    matches.append(section)
        
        return matches


class AcquisitionMetadata(BaseModel):
    """Common acquisition metadata shared across different image types."""
    
    tilt_angle: Optional[float] = Field(None, description="Tilt angle in degrees")
    accumulated_dose: Optional[float] = Field(None, description="Prior dose in e-/A^2")
    exposure_dose: Optional[float] = Field(None, description="Dose for this exposure in e-/A^2")
    dose_rate: Optional[float] = Field(None, description="Dose rate in e-/A^2/s")
    pixel_spacing: Optional[float] = Field(None, description="Pixel spacing in Angstroms")
    defocus: Optional[float] = Field(None, description="Defocus in micrometers")
    exposure_time: Optional[float] = Field(None, description="Exposure time in seconds")
    acquisition_order: Optional[int] = Field(None, description="0-based acquisition order")
    datetime: Optional[str] = Field(None, description="Acquisition timestamp")
    
    # Stage/microscope parameters
    stage_position: Optional[tuple[float, float]] = Field(None, description="Stage X, Y position")
    stage_z: Optional[float] = Field(None, description="Stage Z position")
    magnification: Optional[int] = Field(None, description="Magnification")
    voltage: Optional[int] = Field(None, description="Acceleration voltage in kV")
    
    # CTF parameters
    target_defocus: Optional[float] = Field(None, description="Target defocus in micrometers")
    spot_size: Optional[int] = None
    image_shift: Optional[tuple[float, float]] = None


def parse_xf_file(
    filepath: str, 
) -> dict[str, Any]:
    """
    Parse an .xf file and return a dictionary with projection alignments 
    as sequences of affine and translation transformations.

    Each line in the file should contain six values: a11, a12, a21, a22, dx, dy.

    Returns a dictionary with a list of projection alignments.
    """
    
    projection_alignments = []
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if not line:
            continue
        
        # Parse the six values: a11 a12 a21 a22 dx dy
        values = line.split()
        if len(values) != 6:
            logger.warning(f"Warning: Line {i+1} has {len(values)} values instead of 6, skipping")
            continue
        
        try:
            a11, a12, a21, a22, dx, dy = [float(v) for v in values]
        except ValueError as e:
            logger.warning(f"Warning: Could not parse line {i+1}: {line}, error: {e}")
            continue
        
        affine_transform = {
            "type": "affine",
            "name": f"rotation_projection_{i}",
            "output": f"rotated_projection_{i}",
            "affine": [
                [a11, a12, 0.0],
                [a21, a22, 0.0],
                [0.0, 0.0, 1.0]
            ]
        }
        
        translation_transform = {
            "type": "translation",
            "name": f"translation_projection_{i}",
            "input": f"rotated_projection_{i}",
            "translation": [dx, dy]
        }
        
        projection_alignment = {
            "type": "sequence",
            "name": f"alignment_projection_{i}",
            "sequence": [affine_transform, translation_transform]
        }
        
        projection_alignments.append(projection_alignment)
    
    alignment = {
        "projection_alignments": projection_alignments
    }
    
    return alignment


def parse_mdoc_file(
    filepath: str
) -> MdocFile:
    """
    Parse an .mdoc file containing metadata about tilt series and movie frames .
    Return a MdocFile object.
    """
    mdoc = MdocFile(filename=filepath)
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    current_section = None
    in_global_headers = True
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Handle comments (lines starting with [T = )
        if line.startswith('[T =') and line.endswith(']'):
            # comment = line[4:-1].strip()  # Remove [T = and ]
            # mdoc.comments.append(comment)
            continue
        
        # Handle ZValue sections
        z_value_match = re.match(r'\[ZValue\s*=\s*(\d+)\]', line)
        if z_value_match:
            z_value = int(z_value_match.group(1))
            current_section = ZValueSection(z_value=z_value)
            mdoc.z_sections.append(current_section)
            in_global_headers = False
            continue
        
        # Handle key-value pairs
        if '=' in line and not line.startswith('['):
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Parse value to appropriate type
            parsed_value = parse_value(value)
            
            # Add to appropriate section
            if in_global_headers:
                mdoc.global_headers[key] = parsed_value
            elif current_section is not None:
                current_section.metadata[key] = parsed_value
    
    return mdoc


def parse_value(value_str: str) -> Union[str, int, float]:
    """
    Parse a string value to appropriate type (int, float, or str)
    """
    value_str = value_str.strip()
    
    # Try integer first
    try:
        return int(value_str)
    except ValueError:
        pass
    
    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass
    
    # Return as string
    return value_str


def parse_acquisition_metadata(
        z_section: ZValueSection
    ) -> AcquisitionMetadata:

    metadata = z_section.metadata
    
    stage_pos = None
    if "StagePosition" in metadata:
        pos_str = metadata["StagePosition"].split()
        stage_pos = (float(pos_str[0]), float(pos_str[1]))
    
    image_shift = None
    if "ImageShift" in metadata:
        shift_str = metadata["ImageShift"].split()
        image_shift = (float(shift_str[0]), float(shift_str[1]))
    
    return AcquisitionMetadata(
        tilt_angle=metadata.get("TiltAngle"),
        accumulated_dose=metadata.get("PriorRecordDose"),
        exposure_dose=metadata.get("ExposureDose"),
        dose_rate=metadata.get("DoseRate"),
        pixel_spacing=metadata.get("PixelSpacing"),
        defocus=metadata.get("Defocus"),
        exposure_time=metadata.get("ExposureTime"),
        acquisition_order=z_section.z_value,  # z_value is the acquisition order
        datetime=metadata.get("DateTime"),
        stage_position=stage_pos,
        stage_z=metadata.get("StageZ"),
        magnification=metadata.get("Magnification"),
        voltage=None,  # Will get from global headers
        target_defocus=metadata.get("TargetDefocus"),
        spot_size=metadata.get("SpotSize"),
        image_shift=image_shift,
    )


def match_mdoc_path_to_empiar(
    mdoc_subframe_path: str,
    filter_pattern: str,
    file_pattern: str,
    empiar_files: empiar_utils.EMPIARFileList,
) -> tuple[str, tuple]:
    """
    Match an mdoc SubFramePath to an EMPIAR file.
    
    Args:
        mdoc_subframe_path: Path from mdoc (e.g., "\\struct\\...\\TS_006_00001_-0.0.tif")
        filter_pattern: Pattern to extract variables from end of mdoc path (e.g., "TS_006_{}_{}.tif")
        file_pattern: Pattern to construct EMPIAR path (e.g., "Control/frames/TS_006_{}_{}.tif")
        empiar_files: List of EMPIAR files to search
        
    Returns:
        Matching EMPIAR file path, values from subframe path that match pattern
    """

    normalized_mdoc_path = re.sub(r'[\\]+', '/', mdoc_subframe_path)
    
    result = parse.parse(filter_pattern, normalized_mdoc_path.split("/")[-1])
    
    if result is None:
        raise ValueError(f"MDOC SubFramePath '{normalized_mdoc_path}' does not match filter pattern '{filter_pattern}'")
    
    expected_empiar_path = file_pattern.format(*result.fixed)
    
    for file in empiar_files.files:
        if str(file.path) == expected_empiar_path:
            return str(file.path), result.fixed
    
    raise ValueError(f"No EMPIAR file found matching expected path '{expected_empiar_path}' derived from MDOC SubFramePath '{normalized_mdoc_path}'")
