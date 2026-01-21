import logging
import os
import pandas as pd
import requests

from bia_shared_datamodels import ro_crate_models
from pathlib import Path
from typing import Any
from urllib.parse import quote


logger = logging.getLogger("__main__." + __name__)


def generate_relative_filelist_path(dataset_path: str) -> str:
    return str(Path(dataset_path) / f"file_list.tsv")


def create_file_list(
    output_ro_crate_path: Path, 
    cets_data: dict[str, Any], 
    cets_definition: dict, 
    datasets_map: dict[str, ro_crate_models.Dataset],
) -> list[
    ro_crate_models.FileList | ro_crate_models.TableSchema | ro_crate_models.Column
]:
    """
    Unlike biostudies, all EMPIAR file lists have the same schema.

    Note will created a filelist for 'unnasigned' files that do not match any dataset if there are any. This is not expected to be ingested to the api.
    """

    columns = get_column_list()
    schema = get_schema(columns)

    file_df = build_dataframe_from_cets_data(cets_data)
    print(f"FILE LIST DF:\n{file_df}")

    # path_pattern_objects = get_file_patterns_matches_and_objects(
    #     yaml_file, empiar_api_entry, datasets_map
    # )

    # file_list_df = expand_dataframe_metadata(path_pattern_objects, file_df)

    # dataframes_by_dataset_map = split_dataframe_by_dataset(file_list_df)

    # ro_crate_objects: list = [schema]
    # ro_crate_objects.extend(columns)

    # for dataset_id, dataframe in dataframes_by_dataset_map.items():
    #     file_list_id = generate_relative_filelist_path(dataset_id)
    #     ro_crate_objects.append(get_ro_crate_filelist(file_list_id, schema))
    #     write_filelist(output_ro_crate_path, file_list_id, dataframe)

    # return ro_crate_objects


def create_file_list_for_images(cets_data: dict) -> list[dict[str, Any]]:
    
    file_list = []
    
    # TODO: post-validation, are all levels guaranteed to exist?
    cets_dataset_name = cets_data["name"]
    for region in cets_data["regions"]:
        cets_region_name = region["name"]
        roc_dataset_id = quote(f"{cets_dataset_name} {cets_region_name}/")

        common_image_data = {
            "type": "http://bia/Image", 
            "dataset_ref": roc_dataset_id,
        }

        for movie_stack_collections in region.get("movie_stack_collections", []):
            for movie_stack in movie_stack_collections.get("movie_stacks", []):
                for stack in movie_stack.get("stacks", []):
                    images = stack.get("images", [])
                    
                    # If all images have paths, create entries for each
                    # Otherwise use parent path
                    all_have_paths = all(
                        image.get("path") is not None 
                        for image in images
                    )
                    
                    if all_have_paths and images:
                        for image in images:
                            file_list.append({
                                **common_image_data,
                                "file_path": image["path"],
                                "size_in_bytes": get_file_size(image["path"]), 
                                "label": f"{stack['name']}_{image['section']}", 
                            })
                    else:
                        if stack_path := stack.get("path"):
                            file_list.append({
                                **common_image_data,
                                "file_path": stack_path,
                                "size_in_bytes": get_file_size(stack_path), 
                                "label": stack["name"], 
                            })
        
        for tilt_series in region.get("tilt_series", []):
            
            images = tilt_series.get("images", [])
            
            all_have_paths = all(
                image.get("path") is not None 
                for image in images
            )
            
            if all_have_paths and images:
                for image in images:
                    file_list.append({
                        **common_image_data,
                        "file_path": image["path"],
                        "size_in_bytes": get_file_size(image["path"])
                    })
            else:
                if stack_path := stack.get("path"):
                    file_list.append({
                        **common_image_data,
                        "file_path": stack_path,
                        "size_in_bytes": get_file_size(stack_path)
                    })
    
    return file_list


def get_file_size(file_path: str) -> int | None:
    """
    Determine file size from path.
    
    Strategies:
    1. If local file exists, use os.path.getsize()
    2. If HTTP/HTTPS, use HEAD request to get Content-Length
    3. (TODO) do same for S3 objects
    """

    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    
    # HTTP/HTTPS URL
    if file_path.startswith(("http://", "https://")):
        try:
            response = requests.head(
                file_path, 
                timeout=10 
            )
            response.raise_for_status()
            
            if "Content-Length" in response.headers:
                return int(response.headers["Content-Length"])
            else:
                return None
        except requests.RequestException as e:
            logger.info(f"Failed to get HTTP size for {file_path}: {e}")
            return None
    
    # TODO: support S3
    
    return None


def build_dataframe_from_cets_data(cets_data: dict) -> pd.DataFrame:

    file_list = []
    file_list += create_file_list_for_images(cets_data)

    file_df = pd.DataFrame(file_list)
    return file_df


def get_schema(columns_for_schema: list[ro_crate_models.Column]) -> ro_crate_models.TableSchema:

    tableSchema = {
        "@id": "_:ts0",
        "@type": ["csvw:Schema"],
        "column": [{"@id": column.id} for column in columns_for_schema],
    }
    schema = ro_crate_models.TableSchema(**tableSchema)
    return schema


def get_column_list() -> list[ro_crate_models.Column]:
    
    columns_properties = {
        "file_path": "http://bia/filePath",
        "size_in_bytes": "http://bia/sizeInBytes",
        "type": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "label": "http://schema.org/name",
        "source_image_label": "http://bia/sourceImageLabel",
    }

    id_no = 0
    columns = []

    for column_header, property in columns_properties.items():
        model_dict = {
            "@id": f"_:col{id_no}",
            "@type": ["csvw:Column"],
            "columnName": column_header,
        }
        if property:
            model_dict["propertyUrl"] = property
        columns.append(ro_crate_models.Column(**model_dict))
        id_no += 1

    return columns
