from pathlib import Path

from cets_empiar.settings import get_settings


def make_local_data_path(
        accession_id: str,
        file_type: str,
        file_label: str,
) -> Path:
    
    default_cache_dir = get_settings().default_cache_dir

    dirpath = default_cache_dir / f"{accession_id}/{file_type}"
    dirpath.mkdir(exist_ok=True, parents=True)
    path = dirpath / f"{file_label}.json"

    return path
