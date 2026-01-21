import json
import logging
import mrcfile
import numpy as np
import os
from enum import Enum
from pathlib import Path
from PIL import Image
from typing import Union

from cets_data_model.models.models import Dataset

from cets_empiar.cets_utils import dict_to_cets_model
from cets_empiar.settings import get_settings
from cets_empiar.thumbnails.thumbnail_image_utils import (
    download_mrc_file, 
    get_transformed_annotation_coordinates, 
    project_and_scale_coordinates, 
    make_tomogram_projection, 
    convert_projection_to_rgb_thumbnail, 
    plot_annotation_points_on_image
)


logger = logging.getLogger(__name__)


class ProjectionMethod(str, Enum):
    mean = "mean"
    maximum = "max"
    middle = "middle"


def create_tomogram_thumbnail(
        tomogram_data: np.ndarray, 
        thumbnail_size: tuple[int, int],
        coordinates: list[tuple[float, float]],
        projection_method: str, 
        limit_projection: float
) -> list[Image.Image]:
    
    projection = make_tomogram_projection(
        tomogram_data, 
        projection_method, 
        limit_projection, 
    )
    
    # TODO: establish convention for orientation of axes
    # in cases seen so far, projection requires flipping vertically
    projection = np.flipud(projection) 

    thumbnail_img = convert_projection_to_rgb_thumbnail(
        projection, 
        thumbnail_size, 
    )
    
    thumbnail_img_list = []
    if coordinates:
        for coordinate_set in coordinates:
            thumbnail_img_with_plot = plot_annotation_points_on_image(
                thumbnail_img, 
                coordinate_set
            )
            thumbnail_img_list.append(thumbnail_img_with_plot)
    else:
        thumbnail_img_list.append(thumbnail_img)
        
    return thumbnail_img_list


def process_tomogram_thumbnail(
        accession_id: str, 
        tomograms: list, 
        annotations: Union[list, None], 
        thumbnail_size: tuple[int, int], 
        projection_method: str, 
        limit_projection: float, 
        limit_annotation: float, 
):
    
    default_cets_output_dir = get_settings().default_cets_output_dir
    default_cache_dir = get_settings().default_cache_dir

    output_dir = default_cets_output_dir / f"/{accession_id}/thumbnails"
    output_dir.mkdir(exist_ok=True, parents=True)

    cache_dirpath = default_cache_dir / f"{accession_id}"/"files"
    cache_dirpath.mkdir(exist_ok=True, parents=True)

    for tomogram in tomograms:

        tomo_path = tomogram["path"]
        filename = os.path.basename(tomo_path).replace(".mrc", "")
        cache_filename = f"cache_{filename}.mrc"

        cache_filepath = os.path.join(cache_dirpath, cache_filename)
        if os.path.exists(cache_filepath):
            logger.info(f"Using cached file: {cache_filepath}")
        else:
            logger.info(f"Downloading tomogram from: {tomo_path}")
            download_mrc_file(tomo_path, cache_filepath)

        with mrcfile.open(cache_filepath, mode="r") as mrc:
            tomo_data = mrc.data.copy()
        
        # TODO: support other annotations types (only point_set_3D currently)
        projected_coords = []
        if annotations is not None:
            for annotation in annotations:
                # json_file_path = annotation["path"]
                # original_coords = load_star_coordinates_from_json(json_file_path)

                annotation_coords = get_transformed_annotation_coordinates(
                    annotation, 
                    tomogram
                )
                projected_coords.append(project_and_scale_coordinates(
                    annotation_coords, 
                    tomo_data.shape, 
                    thumbnail_size, 
                    limit_annotation, 
                ))

        thumbnails = create_tomogram_thumbnail(
            tomo_data, 
            thumbnail_size, 
            projected_coords, 
            projection_method, 
            limit_projection, 
        )
        
        for i, thumbnail in enumerate(thumbnails):
            annotation_method = f"annotation_{i}_" if annotations else ""
            thumbnail_path = os.path.join(output_dir, f"{filename}_{projection_method}_{annotation_method}thumbnail.png")
            thumbnail.save(thumbnail_path)


def create_cets_data_thumbnails(
        accession_id: str, 
        thumbnail_size: tuple[int, int], 
        projection_method: ProjectionMethod, 
        limit_projection: float, 
        limit_annotation: float
):

    dataset_file_path = Path(f"local-data/{accession_id}/dataset/{accession_id}.json")
    if not os.path.exists(dataset_file_path):
        raise FileNotFoundError(f"File {dataset_file_path} not found.")

    with open(dataset_file_path, 'r') as f:
        dataset_dict = json.load(f)
    
    dict_to_cets_model(dataset_dict, Dataset)

    for region in dataset_dict["regions"]:
        if region["tomograms"] is not None:
            process_tomogram_thumbnail(
                accession_id, 
                region["tomograms"], 
                region["annotations"], 
                thumbnail_size, 
                projection_method.value, 
                limit_projection, 
                limit_annotation, 
            )