import cets_data_model.models.models as cets_models
import json
import logging
import os 
import yaml

from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from cets_empiar.cets_utils import dict_to_cets_model
from cets_empiar.cets_to_ro_crate.entity_conversion import (
    dataset, 
    file_list, 
)
from cets_empiar.cets_to_ro_crate.ro_crate_defaults import (
    ROCrateCreativeWork,
    get_default_context,
    write_ro_crate_metadata,
    create_ro_crate_folder,
)


logger = logging.getLogger("__main__." + __name__)


def convert_cets_to_ro_crate(
    cets_json_path: Path, 
    definition_path: Path, 
    crate_path: Path | None
):
    
    if not os.path.exists(cets_json_path):
        raise FileNotFoundError(f"File {cets_json_path} not found.")
    with open(cets_json_path) as f:
        cets_data = json.load(f)

    dict_to_cets_model(cets_data, cets_models.Dataset)

    with open(definition_path) as f:
        cets_definition = yaml.safe_load(f)
    
    cets_name = cets_data["name"]
    ro_crate_dir = create_ro_crate_folder(cets_name, crate_path)
    
    graph = []

    # roc_annotation_methods = get_annotation_methods(cets_data, cets_proposal)
    # graph += roc_annotation_methods
    
    # roc_protocols = get_protocols(cets_data, cets_proposal)
    # graph += roc_protocols
    
    # Get datasets (with internal tomogram/annotation data)
    roc_dataset_map = dataset.get_datasets_from_cets(cets_data)
    graph += roc_dataset_map.values()

    roc_file_lists = file_list.create_file_list(ro_crate_dir, cets_data, cets_definition, roc_dataset_map)
    #graph += roc_file_lists
    
    graph.append(ROCrateCreativeWork())
    context = get_default_context()
    
    write_ro_crate_metadata(ro_crate_dir, context, graph)
