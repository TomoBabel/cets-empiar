import json
import logging
import starfile
from typing import Optional, Any
from pandas import DataFrame
from pathlib import Path

from cets_empiar.utils import make_local_data_path
from cets_empiar.empiar_to_cets.utils.empiar_utils import download_file_from_empiar


logger = logging.getLogger(__name__)


def filter_starfile_df(
        star_df: DataFrame, 
        tomogram_column: str,
        image_name: str
) -> DataFrame:
    
    return star_df[star_df[f"{tomogram_column}"] == image_name]


def load_and_filter_annotation_star_file(
        accession_id: str, 
        star_label: str, 
        file_name: str, 
        image_name: str | None, 
        tomogram_column: str | None = None
) -> str:
    
    local_data_path = make_local_data_path(
        accession_id, 
        file_type="star", 
        file_label=star_label
    )

    if Path(local_data_path).exists():
        return str(local_data_path)
    
    temp_star_path = download_file_from_empiar(accession_id, file_name)

    try: 
        star_df = starfile.read(temp_star_path)
        if image_name:
            tomogram_column = tomogram_column or "rlnMicrographName"
            star_df = filter_starfile_df(star_df, tomogram_column, image_name)

        star_df.to_json(local_data_path, orient='records', indent=2)

        return str(local_data_path)
        
    finally:
        Path(temp_star_path).unlink()


def extract_coordinates_from_star_json(coordinate_data: list) -> list:

    coordinates = []
    for entry in coordinate_data:
        x = entry.get("rlnCoordinateX")
        y = entry.get("rlnCoordinateY") 
        z = entry.get("rlnCoordinateZ")
        
        if all(coord is not None for coord in [x, y, z]):
            coordinates.append([float(x), float(y), float(z)])
    
    return coordinates


def identify_pixel_unit_for_star_coordinates(coordinate_dict: dict) -> float | None:

    possible_keys = ["rlnPixelSize", "rlnImagePixelSize", "_pixelSize"]

    for key in possible_keys:
        if key in coordinate_dict:
            return float(coordinate_dict[key])
    
    return None


def get_coordinates_and_units_from_star_json(json_file_path: str) -> tuple[list, Optional[float]]:

    with open(json_file_path, 'r') as f:
        coordinate_data = json.load(f)

    coordinates = extract_coordinates_from_star_json(coordinate_data)
    if coordinates:
        x_coords, y_coords, z_coords = zip(*coordinates)
        logger.info(f"X range: {min(x_coords)} to {max(x_coords)}")
        logger.info(f"Y range: {min(y_coords)} to {max(y_coords)}")
        logger.info(f"Z range: {min(z_coords)} to {max(z_coords)}")
    
    pixel_size = identify_pixel_unit_for_star_coordinates(coordinate_data[0])
    if pixel_size:
        pixel_size = (pixel_size, pixel_size, pixel_size)

    return coordinates, pixel_size
