import inflection
import logging
import parse
import re
from pydantic import BaseModel, Field
from typing import Any, List, Union

from cets_empiar.empiar_to_cets.utils import empiar_utils

logger = logging.getLogger(__name__)


class ZValueSection(BaseModel):
    """
    Represents a single [ZValue = n] section from an .mdoc file.
    """

    z_value: int
    tilt_angle: float | None = None
    sub_frame_path: str | None = None
    num_sub_frames: int | None = None
    prior_record_dose: float | None = None
    frame_doses_and_number: list[float] | None = None
    exposure_dose: float | None = None
    stage_position: list[float] | None = None

    # TODO: determine frequency/utility of other occurring fields in mdocs


class MdocFile(BaseModel):
    """
    Represents a parsed .mdoc file with global headers and ZValue sections.
    """

    filename: str
    tilt_axis_angle: float | None = None
    binning: int | None = None
    image_size: list[int] | None = None
    pixel_spacing: float | None = None
    data_mode: int | None = None
    voltage: float | None = None
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
                subframe_path = section.sub_frame_path
                if not subframe_path:
                    continue
                    
                subframe_path = str(subframe_path)
                
                if not case_sensitive:
                    subframe_path = subframe_path.lower()
                    search_string = search_string.lower()
                
                if subframe_path.endswith(search_string):
                    matches.append(section)
        
        return matches


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


def parse_header_section(line: str) -> dict:
    """
    Parse [T = key1 = value1, key2 = value2, ...] format
    Handles both comma-separated and space-separated pairs.
    Returns empty dict if the T section only contains descriptive text.
    """
    content = line.strip()[1:-1] 
    
    # Split off the section identifier (T)
    _, rest = content.split("=", 1)
    rest = rest.strip()
    
    # Check if this looks like metadata (has = signs after the first one)
    if "=" not in rest:
        # Just descriptive text like "SerialEM: Digitized on..."
        return {}
    
    # Use regex to find all "key = value" patterns
    # Pattern: capture everything before =, the =, and the value (until next key= or comma or end)
    pattern = r'([^=,]+?)\s*=\s*([^=,]+?)(?=\s+[^=,]+\s*=|,|$)'
    matches = re.findall(pattern, rest)
    
    data = {}
    for key, value in matches:
        key = key.strip()
        value = value.strip()
        
        key_field = parse_key(key.replace(" ", "_"))
        parsed_value = parse_value(value)
        
        data[key_field] = parsed_value
    
    return data


def parse_key(key_str: str) -> str:
    """
    Convert PascalCase mdoc fields into snake case for mdoc model.
    """

    key_str = key_str.strip()
    return inflection.underscore(key_str)


def parse_value(value_str: str) -> Union[str, int, float, list]:
    """
    Parse a string value to appropriate type (int, float, list, or str)
    """
    value_str = value_str.strip()
    
    if " " in value_str:
        parts = value_str.split()
        parsed_parts = []
        for part in parts:
            try:
                val = int(part)
            except ValueError:
                try:
                    val = float(part)
                except ValueError:
                    val = part
            parsed_parts.append(val)
        return parsed_parts
    
    try:
        return int(value_str)
    except ValueError:
        pass
    
    try:
        return float(value_str)
    except ValueError:
        pass
    
    return value_str


def parse_mdoc_file(filepath: str, json_output_path: str | None = None) -> MdocFile:
    """
    Parse an .mdoc file containing metadata about tilt series and movie frames.
    Return a MdocFile object.
    """
    header_data = {}
    z_sections = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_section = {}
    in_z_section = False
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # T section may contain metadata or just info text
        if line.startswith('[T ='):
            t_section_data = parse_header_section(line)
            if t_section_data:
                header_data.update(t_section_data)
            continue
        
        z_value_match = re.match(r'\[ZValue\s*=\s*(\d+)\]', line)
        if z_value_match:
            if in_z_section and current_section:
                z_sections.append(ZValueSection(**current_section))
            
            z_value = int(z_value_match.group(1))
            current_section = {"z_value": z_value}
            in_z_section = True
            continue
        
        if '=' in line and not line.startswith('['):
            key, value = line.split('=', 1)
            parsed_key = parse_key(key)
            parsed_value = parse_value(value)
            
            if in_z_section:
                current_section[parsed_key] = parsed_value
            else:
                header_data[parsed_key] = parsed_value
    
    if in_z_section and current_section:
        z_sections.append(ZValueSection(**current_section))
    
    return MdocFile(
        filename=json_output_path if json_output_path else filepath,
        z_sections=z_sections,
        **header_data
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
