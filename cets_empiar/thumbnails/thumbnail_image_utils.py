import json
import logging
import mrcfile
import numpy as np
import os
import requests
from pathlib import Path
from PIL import Image, ImageDraw
from typing import Union

from ..config import settings


logger = logging.getLogger(__name__)


def download_mrc_file(
        url: str, 
        cache_filepath: str, 
        expected_size: int | None
):
    
    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        content_length = response.headers.get('content-length')
        if content_length and expected_size:
            if int(content_length) != expected_size:
                raise ValueError(f"Size mismatch: expected {expected_size}, got {content_length}")
        
        with open(cache_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1048576): # 1 MB chunks
                if chunk:
                    f.write(chunk)
        
        final_size = os.path.getsize(cache_filepath)
        logger.info(f"Download complete: {final_size:,} bytes")
        
        try:
            with mrcfile.open(cache_filepath, mode='r', permissive=True) as mrc:
                _ = mrc.data.shape  # Just check it can be read
        except Exception as e:
            os.unlink(cache_filepath)
            raise ValueError(f"Downloaded file is not a valid MRC: {e}") from e
            
    except requests.RequestException as e:
        if os.path.exists(cache_filepath):
            os.unlink(cache_filepath)
        raise Exception(f"Failed to download {url}: {e}") from e


def load_star_coordinates_from_json(
        json_file_path: str
) -> list[tuple[float, float, float]]:
    
    with open(json_file_path, 'r') as f:
        star_data = json.load(f)
    
    coordinates = []
    for entry in star_data:
        x = entry["rlnCoordinateX"]
        y = entry["rlnCoordinateY"] 
        z = entry["rlnCoordinateZ"]
        coordinates.append((x, y, z))
    
    return coordinates


def check_coordinate_systems_without_transformation(
        anno_coordinate_systems: list[dict], 
        tomo_coordinate_systems: list[dict]
):  
    anno_cs_names = {cs["name"] for cs in anno_coordinate_systems}
    tomo_cs_names = {cs["name"] for cs in tomo_coordinate_systems}

    if common_cs := anno_cs_names & tomo_cs_names:
        if len(common_cs) == 1:
            return
        raise ValueError("Multiple common coordinate systems for annotation and tomogram, cannot tell which to use.")
    
    raise ValueError("No common coordinate systems for annotation and tomogram.")


def check_coordinate_system_with_transformation(
        anno_coordinate_transformations: list[dict], 
        anno_coordinate_systems: list[dict], 
        tomo_coordinate_systems: list[dict]
) -> dict:
    
    anno_cs_names = {cs["name"] for cs in anno_coordinate_systems}
    tomo_cs_names = {cs["name"] for cs in tomo_coordinate_systems}
    
    for transformation in anno_coordinate_transformations:
        input_cs = transformation["input"]
        output_cs = transformation["output"]

        if (
            input_cs in tomo_cs_names and output_cs in anno_cs_names
            or input_cs in anno_cs_names and output_cs in tomo_cs_names
        ): 
            return transformation
    
    raise ValueError("Annotation coordinate system doesn't have a transformation to/from tomogram coordinate system")


def apply_coordinate_transformation(
        coordinates, 
        transformation
) -> list[tuple[float, float, float]] | None:
    
    if transformation["transformation_type"] == "scale":
        scale_factors = transformation["scale"]
        transformed_coordinates = [
            (x * scale_factors[0], y * scale_factors[1], z * scale_factors[2]) 
            for x, y, z in coordinates
        ]
        return transformed_coordinates
    else:
        raise NotImplementedError(f"Transformation type {transformation['transformation_type']} not supported yet.")


def get_transformed_point_set_3D_coordinates(
        annotation: dict, 
        tomogram: dict
) -> list[tuple[float, float, float]]:
    
    coordinates = annotation.get("origin3D", [])
    if not coordinates:
        raise ValueError("No 'origin3D' field found in point_set_3D annotation.")
    
    anno_coordinate_transformations = annotation.get("coordinate_transformations", [])
    anno_coordinate_systems = annotation.get("coordinate_systems", [])
    tomo_coordinate_systems = tomogram.get("coordinate_systems", [])

    if not anno_coordinate_systems or not tomo_coordinate_systems:
        raise ValueError("Coordinate systems missing in annotation and/or tomogram.")
    
    if not anno_coordinate_transformations:
        check_coordinate_systems_without_transformation(
            anno_coordinate_systems, 
            tomo_coordinate_systems
        )
    else:
        transformation_to_apply = check_coordinate_system_with_transformation(
            anno_coordinate_transformations, 
            anno_coordinate_systems, 
            tomo_coordinate_systems
        )
        coordinates = apply_coordinate_transformation(
            coordinates, 
            transformation_to_apply
        )
    
    return coordinates


def get_transformed_annotation_coordinates(
        annotation: dict, 
        tomogram: dict
) -> list[tuple[float, float, float]]:
    
    if annotation["type"] == "point_set_3D":
        return get_transformed_point_set_3D_coordinates(annotation, tomogram)
    else:
        raise NotImplementedError(f"Annotation type {annotation['type']} not supported yet.")


def filter_coordinates_by_depth(
    coordinates: list[tuple[float, float, float]], 
    depth: float, 
    limit_proportion: float
) -> list[tuple[float, float]]:
    """Filter 3D coordinates to 2D based on proximity to center depth."""
    
    center_depth = depth / 2.0
    max_deviation = depth * limit_proportion
    
    return [
        (x, y) 
        for x, y, z in coordinates 
        if abs(z - center_depth) <= max_deviation
    ]


def project_and_scale_coordinates(
    coordinates: list[tuple[float, float, float]],
    tomogram_shape: tuple[int, int, int], 
    thumbnail_size: tuple[int, int], 
    limit_annotation: float
) -> list[tuple[float, float]]:
    
    tomo_depth, tomo_width, tomo_height = tomogram_shape
    
    coords_2d = filter_coordinates_by_depth(coordinates, tomo_depth, limit_annotation)
    
    scale_x = thumbnail_size[0] / tomo_width 
    scale_y = thumbnail_size[1] / tomo_height 
    
    return [(x * scale_x, y * scale_y) for x, y in coords_2d]


def make_tomogram_projection(
        tomogram_data: np.ndarray, 
        projection_method: str, 
        limit_projection: float, 
) -> np.ndarray:
    
    depth = tomogram_data.shape[0]
    if limit_projection < 1.0:
        half_window = (depth * limit_projection) / 2
        stack_centre = (depth -1 ) / 2
        start_slice = round(max(0, stack_centre - half_window))
        end_slice = round(min(depth, stack_centre + half_window))
        tomogram_data = tomogram_data[start_slice:end_slice, :, :]
        logger.info(f"Projecting over slices {start_slice} to {end_slice} (total {end_slice - start_slice})")

    if projection_method == "max":
        projection = np.max(tomogram_data, axis=0)
    elif projection_method == "mean":
        projection = np.mean(tomogram_data, axis=0)
    elif projection_method == "middle":
        middle_idx = tomogram_data.shape[0] // 2
        projection = tomogram_data[middle_idx]
    else:
        raise ValueError("Method must be 'max', 'mean', or 'middle'")

    return projection


def convert_projection_to_rgb_thumbnail(
        projection: np.ndarray, 
        thumbnail_size: tuple[int, int], 
) -> Image.Image:
    
    projection = projection.astype(np.float64)
    projection = (projection - projection.min()) / (projection.max() - projection.min())
    projection = (projection * 255).astype(np.uint8)

    img = Image.fromarray(projection, mode='L')
    img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
    img = img.convert('RGB')

    return img


def plot_annotation_points_on_image(
        thumbnail_img: Image.Image, 
        coordinates: list[tuple[float, float]],
) -> Image.Image:
    
    draw = ImageDraw.Draw(thumbnail_img)
    point_size = 3
    point_color = (0, 255, 255, 64) 
    for x, y in coordinates:
        left = x - point_size
        top = y - point_size
        right = x + point_size
        bottom = y + point_size
        
        draw.ellipse([left, top, right, bottom], 
                    fill=None, 
                    outline=point_color)
    
    return thumbnail_img


