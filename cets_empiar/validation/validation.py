import json
import logging
import os
from pathlib import Path
from pydantic import ValidationError
from cets_data_model.models.models import Dataset, Tomogram

from cets_empiar.cets_utils import dict_to_cets_model
from cets_empiar.validation.validator_models.point_annotation import ValidatedPointSet3D


logger = logging.getLogger(__name__)


def validate_cets_annotations(
        tomograms: list, 
        annotations: list, 
): 
    
    for tomogram_dict in tomograms:
        tomogram = Tomogram(**tomogram_dict)
        
        for annotation in annotations:
            try:
                ValidatedPointSet3D.validate_with_tomogram(
                    annotation, 
                    tomogram
                )
                logger.info(f"Validation successful for annotation with {len(annotation.get('origin3D', []))} points")
            except ValidationError as e:
                logger.warning(f"Pydantic validation failure: {e}")
            except ValueError as e:
                logger.warning(f"Coordinate validation failure: {e}")
  

def validate_cets(
        accession_id: str
):
    
    dataset_file_path = Path(f"local-data/{accession_id}/dataset/{accession_id}.json")
    if not os.path.exists(dataset_file_path):
        raise FileNotFoundError(f"File {dataset_file_path} not found.")

    with open(dataset_file_path, 'r') as f:
        dataset_dict = json.load(f)

    dict_to_cets_model(dataset_dict, Dataset)

    for region in dataset_dict["regions"]:
        if (tomograms := region["tomograms"]) is not None and (annotations := region["annotations"]) is not None:
            validate_cets_annotations(tomograms, annotations)