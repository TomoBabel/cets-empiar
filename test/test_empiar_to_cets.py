import json
import pytest
import tempfile

from pathlib import Path
from unittest.mock import patch
from cets_empiar.empiar_to_cets import empiar_conversion
from cets_empiar.empiar_to_cets.utils import empiar_utils
from cets_empiar.empiar_to_cets.parsing import metadata_parsing


@pytest.fixture
def input_data_dir():
    """Return path to input data directory"""
    return Path(__file__).parent / "input_data"


@pytest.fixture
def output_data_dir():
    """Return path to output data directory"""
    return Path(__file__).parent / "output_data"


@pytest.fixture
def test_with_metadata_definition_path(input_data_dir):
    """Path to simulated definition YAML"""
    return input_data_dir / "test_with_metadata_definition.yaml"


@pytest.fixture
def test_without_metadata_definition_path(input_data_dir):
    """Path to simulated definition YAML"""
    return input_data_dir / "test_without_metadata_definition.yaml"


@pytest.fixture
def empiar_file_list(input_data_dir):
    """Load simulated EMPIAR file list"""
    with open(input_data_dir / "empiar_file_list.json") as f:
        data = json.load(f)
    return empiar_utils.EMPIARFileList.model_validate(data)


@pytest.fixture
def mdoc_content(input_data_dir):
    """Load simulated MDOC content"""
    with open(input_data_dir / "TS_001.mdoc") as f:
        return f.read()


@pytest.fixture
def expected_cets_output_with_metadata(output_data_dir):
    """Load expected CETS output"""
    with open(output_data_dir / "expected_cets_output_with_metadata.json") as f:
        return json.load(f)


@pytest.fixture
def expected_cets_output_without_metadata(output_data_dir):
    """Load expected CETS output"""
    with open(output_data_dir / "expected_cets_output_without_metadata.json") as f:
        return json.load(f)


@pytest.fixture
def mock_mrc_header():
    """Simulated MRC header data"""
    return {
        "dimensions": (500, 500, 100),
        "pixel_size": [10.0, 10.0, 10.0]
    }


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_empiar_to_cets_conversion_with_metadata(
    test_with_metadata_definition_path,
    empiar_file_list,
    mdoc_content,
    expected_cets_output_with_metadata,
    mock_mrc_header,
    temp_output_dir
):
    """Test complete EMPIAR to CETS conversion"""
    
    # Mock EMPIAR file list retrieval
    with patch('cets_empiar.empiar_to_cets.empiar_conversion.empiar_utils.get_files_for_empiar_entry_cached') as mock_get_files:
        mock_get_files.return_value = empiar_file_list
        
        # Mock MDOC file download
        with patch('cets_empiar.empiar_to_cets.utils.metadata_utils.download_file_from_empiar') as mock_download:
            # Create temporary MDOC file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mdoc', delete=False) as tmp_mdoc:
                tmp_mdoc.write(mdoc_content)
                tmp_mdoc_path = tmp_mdoc.name
            
            mock_download.return_value = tmp_mdoc_path
            
            # Mock MRC header reading
            with patch('cets_empiar.empiar_to_cets.conversion.entity_conversion.tomogram.read_mrc_header') as mock_read_mrc:
                mock_read_mrc.return_value = mock_mrc_header
                
                empiar_conversion.convert_empiar_entry_to_cets(
                    definition_path=test_with_metadata_definition_path,
                    cets_output_dir=temp_output_dir
                )
                
                output_path = temp_output_dir / "dataset" / "EMPIAR-99999.json"
                assert output_path.exists(), "CETS output file not created"
                
                with open(output_path) as f:
                    actual_output = json.load(f)
                
                assert actual_output["name"] == expected_cets_output_with_metadata["name"]
                assert len(actual_output["regions"]) == len(expected_cets_output_with_metadata["regions"])
                
                actual_region = actual_output["regions"][0]
                expected_region = expected_cets_output_with_metadata["regions"][0]
                
                assert actual_region["id"] == expected_region["id"]
                
                actual_stacks = actual_region["movie_stack_collection"]["movie_stacks"][0]["stacks"]
                expected_stacks = expected_region["movie_stack_collection"]["movie_stacks"][0]["stacks"]
                
                assert len(actual_stacks) == len(expected_stacks)
                
                assert actual_stacks[0]["id"] == expected_stacks[0]["id"]
                assert len(actual_stacks[0]["images"]) == len(expected_stacks[0]["images"])
                
                actual_tilt_series = actual_region["tilt_series"][0]
                expected_tilt_series = expected_region["tilt_series"][0]
                
                assert actual_tilt_series["id"] == expected_tilt_series["id"]
                assert len(actual_tilt_series["images"]) == len(expected_tilt_series["images"])
                
                actual_tomogram = actual_region["tomograms"][0]
                expected_tomogram = expected_region["tomograms"][0]
                
                assert actual_tomogram["id"] == expected_tomogram["id"]
                assert actual_tomogram["width"] == expected_tomogram["width"]
                assert actual_tomogram["height"] == expected_tomogram["height"]
                assert actual_tomogram["depth"] == expected_tomogram["depth"]
                
                Path(tmp_mdoc_path).unlink()


def test_empiar_to_cets_conversion_without_metadata(
    test_without_metadata_definition_path,
    empiar_file_list,
    expected_cets_output_without_metadata,
    mock_mrc_header,
    temp_output_dir
):
    """Test complete EMPIAR to CETS conversion"""
    
    # Mock EMPIAR file list retrieval
    with patch('cets_empiar.empiar_to_cets.empiar_conversion.empiar_utils.get_files_for_empiar_entry_cached') as mock_get_files:
        mock_get_files.return_value = empiar_file_list
        
        # Mock MRC header reading
        with patch('cets_empiar.empiar_to_cets.conversion.entity_conversion.tomogram.read_mrc_header') as mock_read_mrc:
            mock_read_mrc.return_value = mock_mrc_header
            
            empiar_conversion.convert_empiar_entry_to_cets(
                definition_path=test_without_metadata_definition_path,
                cets_output_dir=temp_output_dir
            )
            
            output_path = temp_output_dir / "dataset" / "EMPIAR-99999.json"
            assert output_path.exists(), "CETS output file not created"
            
            with open(output_path) as f:
                actual_output = json.load(f)
            
            assert actual_output["name"] == expected_cets_output_without_metadata["name"]
            assert len(actual_output["regions"]) == len(expected_cets_output_without_metadata["regions"])
            
            actual_region = actual_output["regions"][0]
            expected_region = expected_cets_output_without_metadata["regions"][0]
            
            assert actual_region["id"] == expected_region["id"]
            
            actual_stacks = actual_region["movie_stack_collection"]["movie_stacks"][0]["stacks"]
            expected_stacks = expected_region["movie_stack_collection"]["movie_stacks"][0]["stacks"]
            
            assert len(actual_stacks) == len(expected_stacks)
            
            assert actual_stacks[0]["id"] == expected_stacks[0]["id"]
            assert len(actual_stacks[0]["images"]) == len(expected_stacks[0]["images"])
            
            actual_tilt_series = actual_region["tilt_series"][0]
            expected_tilt_series = expected_region["tilt_series"][0]
            
            assert actual_tilt_series["id"] == expected_tilt_series["id"]
            assert len(actual_tilt_series["images"]) == len(expected_tilt_series["images"])
            
            actual_tomogram = actual_region["tomograms"][0]
            expected_tomogram = expected_region["tomograms"][0]
            
            assert actual_tomogram["id"] == expected_tomogram["id"]
            assert actual_tomogram["width"] == expected_tomogram["width"]
            assert actual_tomogram["height"] == expected_tomogram["height"]
            assert actual_tomogram["depth"] == expected_tomogram["depth"]


def test_mdoc_parsing(mdoc_content):
    """Test MDOC file parsing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mdoc', delete=False) as tmp:
        tmp.write(mdoc_content)
        tmp_path = tmp.name
    
    try:
        mdoc = metadata_parsing.parse_mdoc_file(tmp_path)
        
        assert mdoc.global_headers["ImageSize"] == "3840 2730"
        assert mdoc.global_headers["PixelSpacing"] == 2.15
        assert len(mdoc.z_sections) == 3
        
        assert mdoc.z_sections[0].z_value == 0
        assert mdoc.z_sections[0].metadata["TiltAngle"] == 0.0
        assert mdoc.z_sections[0].metadata["NumSubFrames"] == 5
        
    finally:
        Path(tmp_path).unlink()
