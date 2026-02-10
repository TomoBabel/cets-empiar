import json
import pytest
import tempfile

from pathlib import Path
from unittest.mock import patch
from cets_empiar.empiar_to_cets import empiar_conversion
from cets_empiar.empiar_to_cets.utils import empiar_utils
from cets_empiar.empiar_to_cets.parsing import metadata_parsing


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


def compare_cets_output(actual_path, expected_path):
    """
    Compare CETS JSON output to expected output.
    """
    with open(actual_path) as f:
        actual = json.load(f)
    
    with open(expected_path) as f:
        expected = json.load(f)
    
    # Compare dataset name
    assert actual["name"] == expected["name"], f"Dataset name mismatch: {actual['name']} != {expected['name']}"
    
    # Compare regions count
    assert len(actual["regions"]) == len(expected["regions"]), \
        f"Number of regions mismatch: {len(actual['regions'])} != {len(expected['regions'])}"
    
    for i, (actual_region, expected_region) in enumerate(zip(actual["regions"], expected["regions"])):
        # Region ID
        assert actual_region["id"] == expected_region["id"], \
            f"Region {i} ID mismatch: {actual_region['id']} != {expected_region['id']}"
        
        # Movie stack collection
        if "movie_stack_collection" in expected_region:
            assert "movie_stack_collection" in actual_region, f"Region {i} missing movie_stack_collection"
            
            actual_msc = actual_region["movie_stack_collection"]
            expected_msc = expected_region["movie_stack_collection"]
            
            # Movie stacks
            actual_ms_list = actual_msc["movie_stacks"]
            expected_ms_list = expected_msc["movie_stacks"]
            assert len(actual_ms_list) == len(expected_ms_list), \
                f"Region {i} movie_stacks count mismatch: {len(actual_ms_list)} != {len(expected_ms_list)}"
            
            for j, (actual_ms, expected_ms) in enumerate(zip(actual_ms_list, expected_ms_list)):
                assert actual_ms["id"] == expected_ms["id"], \
                    f"Region {i} movie_stack {j} ID mismatch"
                
                # Stacks within movie stack
                actual_stacks = actual_ms["stacks"]
                expected_stacks = expected_ms["stacks"]
                assert len(actual_stacks) == len(expected_stacks), \
                    f"Region {i} movie_stack {j} stacks count: {len(actual_stacks)} != {len(expected_stacks)}"
                
                for k, (actual_stack, expected_stack) in enumerate(zip(actual_stacks, expected_stacks)):
                    assert actual_stack["id"] == expected_stack["id"], \
                        f"Stack {k} ID mismatch: {actual_stack['id']} != {expected_stack['id']}"
                    assert actual_stack["path"] == expected_stack["path"], \
                        f"Stack {k} path mismatch"
                    
                    # Images within stack
                    actual_images = actual_stack["images"]
                    expected_images = expected_stack["images"]
                    assert len(actual_images) == len(expected_images), \
                        f"Stack {k} images count: {len(actual_images)} != {len(expected_images)}"
                    
                    for m, (actual_img, expected_img) in enumerate(zip(actual_images, expected_images)):
                        assert actual_img["width"] == expected_img["width"], \
                            f"Stack {k} image {m} width mismatch"
                        assert actual_img["height"] == expected_img["height"], \
                            f"Stack {k} image {m} height mismatch"
                        assert actual_img["nominal_tilt_angle"] == expected_img["nominal_tilt_angle"], \
                            f"Stack {k} image {m} tilt_angle mismatch"
                        assert actual_img["accumulated_dose"] == expected_img["accumulated_dose"], \
                            f"Stack {k} image {m} accumulated_dose mismatch"
                        assert actual_img["section"] == expected_img["section"], \
                            f"Stack {k} image {m} section mismatch"
        
        # Tilt series
        if "tilt_series" in expected_region:
            assert "tilt_series" in actual_region, f"Region {i} missing tilt_series"
            
            actual_ts_list = actual_region["tilt_series"]
            expected_ts_list = expected_region["tilt_series"]
            assert len(actual_ts_list) == len(expected_ts_list), \
                f"Region {i} tilt_series count: {len(actual_ts_list)} != {len(expected_ts_list)}"
            
            for j, (actual_ts, expected_ts) in enumerate(zip(actual_ts_list, expected_ts_list)):
                assert actual_ts["id"] == expected_ts["id"], \
                    f"Tilt series {j} ID mismatch: {actual_ts['id']} != {expected_ts['id']}"
                assert actual_ts["path"] == expected_ts["path"], \
                    f"Tilt series {j} path mismatch"
                assert actual_ts["movie_stack_series_id"] == expected_ts["movie_stack_series_id"], \
                    f"Tilt series {j} movie_stack_series_id mismatch"
                
                # Tilt series images
                actual_ts_images = actual_ts["images"]
                expected_ts_images = expected_ts["images"]
                assert len(actual_ts_images) == len(expected_ts_images), \
                    f"Tilt series {j} images count: {len(actual_ts_images)} != {len(expected_ts_images)}"
                
                for m, (actual_img, expected_img) in enumerate(zip(actual_ts_images, expected_ts_images)):
                    assert actual_img["width"] == expected_img["width"], \
                        f"Tilt series {j} image {m} width mismatch"
                    assert actual_img["height"] == expected_img["height"], \
                        f"Tilt series {j} image {m} height mismatch"
                    assert actual_img["nominal_tilt_angle"] == expected_img["nominal_tilt_angle"], \
                        f"Tilt series {j} image {m} tilt_angle: {actual_img['nominal_tilt_angle']} != {expected_img['nominal_tilt_angle']}"
                    assert actual_img["accumulated_dose"] == expected_img["accumulated_dose"], \
                        f"Tilt series {j} image {m} accumulated_dose mismatch"
                    assert actual_img["section"] == expected_img["section"], \
                        f"Tilt series {j} image {m} section mismatch"
                    assert actual_img["movie_stack_id"] == expected_img["movie_stack_id"], \
                        f"Tilt series {j} image {m} movie_stack_id mismatch"
        
        # Tomograms
        if "tomograms" in expected_region:
            assert "tomograms" in actual_region, f"Region {i} missing tomograms"
            
            actual_tomo_list = actual_region["tomograms"]
            expected_tomo_list = expected_region["tomograms"]
            assert len(actual_tomo_list) == len(expected_tomo_list), \
                f"Region {i} tomograms count: {len(actual_tomo_list)} != {len(expected_tomo_list)}"
            
            for j, (actual_tomo, expected_tomo) in enumerate(zip(actual_tomo_list, expected_tomo_list)):
                assert actual_tomo["id"] == expected_tomo["id"], \
                    f"Tomogram {j} ID mismatch: {actual_tomo['id']} != {expected_tomo['id']}"
                assert actual_tomo["path"] == expected_tomo["path"], \
                    f"Tomogram {j} path mismatch"
                assert actual_tomo["width"] == expected_tomo["width"], \
                    f"Tomogram {j} width: {actual_tomo['width']} != {expected_tomo['width']}"
                assert actual_tomo["height"] == expected_tomo["height"], \
                    f"Tomogram {j} height: {actual_tomo['height']} != {expected_tomo['height']}"
                assert actual_tomo["depth"] == expected_tomo["depth"], \
                    f"Tomogram {j} depth: {actual_tomo['depth']} != {expected_tomo['depth']}"
                assert actual_tomo["tilt_series_id"] == expected_tomo["tilt_series_id"], \
                    f"Tomogram {j} tilt_series_id mismatch"
                
                # Coordinate systems
                assert len(actual_tomo["coordinate_systems"]) == len(expected_tomo["coordinate_systems"]), \
                    f"Tomogram {j} coordinate_systems count mismatch"
                
                # Coordinate transformations
                assert len(actual_tomo["coordinate_transformations"]) == len(expected_tomo["coordinate_transformations"]), \
                    f"Tomogram {j} coordinate_transformations count mismatch"
    
    # Check averages
    assert len(actual.get("averages", [])) == len(expected.get("averages", [])), \
        "Averages count mismatch"
    
    return True


def test_empiar_to_cets_conversion_with_metadata(
    test_with_metadata_definition_path,
    empiar_file_list,
    input_data_dir,
    output_data_dir,
    mock_mrc_header,
    temp_output_dir
):
    """Test complete EMPIAR to CETS conversion with metadata"""
    
    # Mock EMPIAR file list retrieval
    with patch('cets_empiar.empiar_to_cets.empiar_conversion.empiar_utils.get_files_for_empiar_entry_cached') as mock_get_files:
        mock_get_files.return_value = empiar_file_list
        
        # Mock MDOC file download - create a temp copy
        with patch('cets_empiar.empiar_to_cets.utils.metadata_utils.download_file_from_empiar') as mock_download:
            def mock_download_func(accession, pattern):
                # Create a temporary copy so the original doesn't get deleted
                import tempfile
                import shutil
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.mdoc', delete=False)
                shutil.copy(input_data_dir / "TS_001.mdoc", temp_file.name)
                return temp_file.name
            
            mock_download.side_effect = mock_download_func
            
            # Mock MRC header reading
            with patch('cets_empiar.empiar_to_cets.conversion.entity_conversion.tomogram.read_mrc_header') as mock_read_mrc:
                mock_read_mrc.return_value = mock_mrc_header
                
                # Run conversion
                empiar_conversion.convert_empiar_entry_to_cets(
                    definition_path=test_with_metadata_definition_path,
                    cets_output_dir=temp_output_dir
                )
                
                # Compare output
                actual_output_path = temp_output_dir / "dataset" / "EMPIAR-99999.json"
                expected_output_path = output_data_dir / "expected_cets_output_with_metadata.json"
                
                assert actual_output_path.exists(), "CETS output file not created"
                assert compare_cets_output(actual_output_path, expected_output_path)


def test_empiar_to_cets_conversion_without_metadata(
    test_without_metadata_definition_path,
    empiar_file_list,
    output_data_dir,
    mock_mrc_header,
    temp_output_dir
):
    """Test complete EMPIAR to CETS conversion without metadata"""
    
    # Mock EMPIAR file list retrieval
    with patch('cets_empiar.empiar_to_cets.empiar_conversion.empiar_utils.get_files_for_empiar_entry_cached') as mock_get_files:
        mock_get_files.return_value = empiar_file_list
        
        # Mock MRC header reading
        with patch('cets_empiar.empiar_to_cets.conversion.entity_conversion.tomogram.read_mrc_header') as mock_read_mrc:
            mock_read_mrc.return_value = mock_mrc_header
            
            # Run conversion
            empiar_conversion.convert_empiar_entry_to_cets(
                definition_path=test_without_metadata_definition_path,
                cets_output_dir=temp_output_dir
            )
            
            # Compare output
            actual_output_path = temp_output_dir / "dataset" / "EMPIAR-99999.json"
            expected_output_path = output_data_dir / "expected_cets_output_without_metadata.json"
            
            assert actual_output_path.exists(), "CETS output file not created"
            assert compare_cets_output(actual_output_path, expected_output_path)
