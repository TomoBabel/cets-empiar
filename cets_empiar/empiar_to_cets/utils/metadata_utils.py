import json
import logging
import struct
from fs.ftpfs import FTPFS
from pathlib import Path
from typing import Any

from cets_empiar.empiar_to_cets.parsing import metadata_parsing
from cets_empiar.empiar_to_cets.utils.empiar_utils import download_file_from_empiar
from cets_empiar.utils import make_local_data_path


logger = logging.getLogger(__name__)


def save_mdoc_to_json(mdoc: metadata_parsing.MdocFile, filepath: str) -> None:
    
    with open(filepath, 'w') as f:
        f.write(mdoc.model_dump_json(indent=2))


def save_alignment_to_json(alignment: dict[str, Any], filepath: str) -> None:
    
    with open(filepath, 'w') as f:
        json.dump(alignment, f, indent=2)


def load_mdoc_from_json(filepath: str) -> metadata_parsing.MdocFile:
    
    with open(filepath, 'r') as f:
        return metadata_parsing.MdocFile.model_validate_json(f.read())


def load_alignment_from_json(filepath: str) -> dict[str, Any]:
    """Load Alignment object from JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return data


def load_mdoc_file(
    accession_id: str, 
    file_pattern: str,
    mdoc_label: str,
) -> metadata_parsing.MdocFile:
    
    local_data_path = make_local_data_path(
        accession_id, 
        file_type="mdoc", 
        file_label=mdoc_label
    )
    
    if local_data_path.exists():
        return load_mdoc_from_json(str(local_data_path))

    temp_mdoc_path = download_file_from_empiar(accession_id, file_pattern)
    
    try:
        mdoc = metadata_parsing.parse_mdoc_file(temp_mdoc_path)
        save_mdoc_to_json(mdoc, str(local_data_path))
        
        return mdoc
        
    finally:
        Path(temp_mdoc_path).unlink()


def load_xf_file(
    accession_id: str, 
    file_pattern: str,
    xf_label: str,
) -> dict[str, Any]:
    
    local_data_path = make_local_data_path(
        accession_id, 
        file_type="xf", 
        file_label=xf_label
    )
    
    if local_data_path.exists():
        return load_alignment_from_json(str(local_data_path))
    
    temp_xf_path = download_file_from_empiar(accession_id, file_pattern)
    
    try:
        alignment = metadata_parsing.parse_xf_file(temp_xf_path)
        save_alignment_to_json(alignment, str(local_data_path))
        
        return alignment
        
    finally:
        Path(temp_xf_path).unlink()


def read_mrc_header(
    filepath: str
) -> dict[str, Any]:
    """    
    Read metadata from MRC file header from a file located at given filepath.
    Returns a dictionary with header information.
    """
    # TODO: local file version

    ftp_url = "ftp.ebi.ac.uk"

    with FTPFS(ftp_url) as ftp_fs:
        with ftp_fs.open(filepath, "rb") as f:
            header_data = f.read(1024)
    
    # Parse MRC header - according to MRC2014 format - https://www.ccpem.ac.uk/mrc-format/mrc2014/
    # TODO: other MRC formats
    # Format: nx, ny, nz, mode, nxstart, nystart, nzstart, mx, my, mz
    header_ints = struct.unpack("<10i", header_data[:40])
    nx, ny, nz = header_ints[:3]
    mx = header_ints[7] if header_ints[7] > 0 else nx
    my = header_ints[8] if header_ints[8] > 0 else ny
    mz = header_ints[9] if header_ints[9] > 0 else nz

    if not mx or not my or not mz:
        logger.warning(
            f"Warning: MRC header has some zero sampling dimensions (mx, my, mz): {mx}, {my}, {mz}. "
            f"Image dimensions (nx, ny, nz): {nx}, {ny}, {nz} will be used where m_ is zero."
        )

    # Bytes 40-52: cell dimensions (3 floats)
    cell_dims = struct.unpack("<3f", header_data[40:52])
    
    # pixel size should use sampling dimensions (mx, my, mz), if present,
    # # in case image is cropped, not image dimensions (nx, ny, nz) — see block above
    pixel_size = [
        cell_dims[0] / mx, 
        cell_dims[1] / my, 
        cell_dims[2] / mz
    ]

    return {
        "dimensions": (nx, ny, nz),
        "pixel_size": pixel_size
    }
