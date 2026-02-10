import json
import logging

from pathlib import Path
from pydantic import BaseModel, ValidationError
from pydantic.alias_generators import to_snake
from typing import Any, Type

from cets_empiar.settings import get_settings


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


def get_model_type_dir(output_dirpath, model: Type[BaseModel]) -> Path:
    """Get the directory path for a specific model type within this accession"""
    model_type = to_snake(model.__name__)
    return output_dirpath / model_type


def save_cets_model_to_json(
    region_title: str, 
    cets_model: BaseModel, 
    cets_output_dir: Path
) -> None:
    
    if not isinstance(cets_model, BaseModel):
        raise TypeError("Object must be a Pydantic model")
    
    cets_output_dir.mkdir(exist_ok=True, parents=True)

    model_dir = get_model_type_dir(cets_output_dir, cets_model.__class__)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_dir / f"{region_title}.json"

    with open(model_path, 'w') as f:
        json.dump(cets_model.model_dump(), f, indent=2)
    
    logger.info(f"Saved CETS model to {model_path}")

