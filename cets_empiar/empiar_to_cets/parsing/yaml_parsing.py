import re
import yaml

from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List


class MovieMetadata(BaseModel):
    label: str
    file_pattern: str


class MovieStack(BaseModel):
    label: str
    file_pattern: str


class TiltSeriesMetadata(BaseModel):
    label: str
    file_pattern: str


class TiltSeries(BaseModel):
    label: str
    file_pattern: str


class Alignment(BaseModel):
    label: str
    file_pattern: str


class Tomogram(BaseModel):
    label: str
    file_pattern: str


class Annotation(BaseModel):
    label: str
    annotation_type: str
    file_name: str
    image_name: Optional[str] = None
    tomogram_column: Optional[str] = None
    default_coordinate_system: Optional[str] = None


# TODO: should metadata be a list? In what circumstances will there be multiple files, and what formats?
class RegionDefinition(BaseModel):
    name: str
    movie_metadata: Optional[MovieMetadata] = None
    movie_stacks: Optional[List[MovieStack]] = None
    tilt_series_metadata: Optional[TiltSeriesMetadata] = None
    tilt_series: Optional[List[TiltSeries]] = None
    alignments: Optional[Alignment] = None
    tomograms: Optional[List[Tomogram]] = None 
    annotations: Optional[List[Annotation]] = None
    metadata_file: Optional[Path] = None
    tomogram_file_pattern: Optional[str] = None
    tilt_series_file_pattern: Optional[str] = None
    movie_stack_file_pattern: Optional[str] = None
    movie_stack_filter_pattern: Optional[str] = None



def load_empiar_definition_yaml(
        yaml_path: Path, 
) -> tuple[dict, str]:
    
    with open(yaml_path) as f:
        yaml_dict = yaml.safe_load(f)
    accession_id = yaml_dict["accession_id"]

    if not re.match(r'^EMPIAR-\d+$', accession_id):
        raise ValueError(f"Invalid EMPIAR accession ID format: {accession_id}")
    
    return yaml_dict, accession_id   


def parse_regions(
        definition_dict: dict,
) -> list[RegionDefinition]:
    
    regions = []
    for region in definition_dict["regions"]:
        region_definition = RegionDefinition.model_validate(region)
        regions.append(region_definition)
    
    return regions
