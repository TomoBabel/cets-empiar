import json
import logging
import os
import parse
import tempfile
import urllib.request

from fsspec import filesystem
from pathlib import Path
from typing import List
from pydantic import BaseModel

from cets_empiar.settings import get_settings

logger = logging.getLogger(__name__)

EMPIAR_BASE_URL = "https://ftp.ebi.ac.uk/empiar/world_availability/"


class EMPIARFile(BaseModel, frozen=True):
    path: Path
    size_in_bytes: int


class EMPIARFileList(BaseModel):

    files: List[EMPIARFile]


def get_files_matching_pattern(
    file_list: EMPIARFileList, 
    file_pattern: str
) -> list[str]:

    selected_file_references = []
    for file in file_list.files:
        result = parse.parse(file_pattern, str(file.path))
        if result is not None:
            selected_file_references.append(str(file.path))

    if len(selected_file_references) == 0:
        raise ValueError(f"No files found matching pattern: {file_pattern}")
    
    logger.info(f"Found {len(selected_file_references)} file references matching pattern {file_pattern}")

    return selected_file_references


def get_list_of_empiar_files(
    accession_no: str
) -> EMPIARFileList:

    ftp_fs = filesystem('ftp', host='ftp.ebi.ac.uk')
    root_path = f"/empiar/world_availability/{accession_no}/data"

    empiar_files = []

    for dirpath, dirnames, filenames in ftp_fs.walk:
        for filename in filenames:

            full_path = f"{dirpath}/{filename}"
            file_info = ftp_fs.info(full_path)
            
            relpath = Path(dirpath).relative_to(root_path)
            
            empiar_file = EMPIARFile(
                path=relpath / filename,
                size_in_bytes=file_info['size']
            )
            empiar_files.append(empiar_file)

    return EMPIARFileList(files=empiar_files)


def get_files_for_empiar_entry_cached(
    accession_id: str
) -> EMPIARFileList:
    
    default_cache_dir = get_settings().default_cache_dir
    cache_dirpath = default_cache_dir / f"{accession_id}/files"
    cache_dirpath.mkdir(exist_ok=True, parents=True)
    file_list_fpath = cache_dirpath / "all_files.json"

    accession_no = accession_id.split("-")[1]

    if file_list_fpath.exists():
        with open(file_list_fpath) as fh:
            model_data = json.load(fh)
            list_of_files = EMPIARFileList.model_validate(model_data) # type: ignore
    else:
        list_of_files = get_list_of_empiar_files(accession_no)
        with open(file_list_fpath, "w") as fh:
            model_json_str = list_of_files.model_dump_json(indent=2) # type: ignore
            fh.write(model_json_str)

    return list_of_files


def download_file_from_empiar(
    accession_id: str, 
    file_name: str
) -> str:

    accession_no = accession_id.split("-")[1]
    empiar_path = f"{accession_no}/data/{file_name}"
    url = f"{EMPIAR_BASE_URL}{empiar_path}"
    
    file_type = Path(file_name).suffix[1:]
    temp_fd, local_path = tempfile.mkstemp(suffix=f".{file_type}", prefix=f"{file_type}_")
    
    try:
        os.close(temp_fd)
        urllib.request.urlretrieve(url, local_path)
        return local_path
    except Exception as e:
        try:
            os.unlink(local_path)
        except OSError:
            pass
        raise Exception(f"Failed to download {url}: {str(e)}") from e