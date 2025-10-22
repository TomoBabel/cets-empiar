import json
import logging
from pathlib import Path
from typing import Any, Type
from pydantic import BaseModel, ValidationError
from pydantic.alias_generators import to_snake


logger = logging.getLogger(__name__)


def dict_to_cets_model(
    model_data: dict[str, Any], 
    cets_model_class: Type[BaseModel], 
) -> BaseModel:
    
    try:
        return cets_model_class.model_validate(model_data)
    except ValidationError as e:
        logger.error(
            f"Validation error for {cets_model_class.__name__}: {e}"
        )
        raise


def get_model_type_dir(cache_dirpath, model: Type[BaseModel]) -> Path:
    """Get the directory path for a specific model type within this accession"""
    model_type = to_snake(model.__name__)
    return cache_dirpath / model_type


def save_cets_model_to_json(
        accession_id: str,
        region_title: str, 
        cets_model: BaseModel,
) -> None:
    
    if not isinstance(cets_model, BaseModel):
        raise TypeError("Object must be a Pydantic model")
    
    cache_dirpath = Path(f"local-data/{accession_id}")
    cache_dirpath.mkdir(exist_ok=True, parents=True)

    model_dir = get_model_type_dir(cache_dirpath, cets_model.__class__)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_dir / f"{region_title}.json"

    with open(model_path, 'w') as f:
        json.dump(cets_model.model_dump(), f, indent=2)
    
    logger.info(f"Saved CETS model to {model_path}")

