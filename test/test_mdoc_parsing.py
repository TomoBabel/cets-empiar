import json
from cets_empiar.empiar_to_cets.parsing import metadata_parsing


def load_expected_json(output_data_dir, filename):
    """Helper to load expected JSON output"""
    with open(output_data_dir / filename) as f:
        return json.load(f)


def compare_mdoc_to_expected(mdoc, expected):
    """Compare parsed mdoc to expected JSON, handling filename paths"""
    actual = json.loads(mdoc.model_dump_json())
    
    assert actual["filename"] is not None
    expected.pop("filename")
    actual.pop("filename")
    
    assert actual == expected


def test_mdoc_parsing_basic(input_data_dir, output_data_dir):
    """Test basic MDOC file parsing"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_001.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_basic.json")
    compare_mdoc_to_expected(mdoc, expected)


def test_mdoc_parsing_complex(input_data_dir, output_data_dir):
    """Test complex MDOC parsing with multiple T sections and global headers"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_complex.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_complex.json")
    compare_mdoc_to_expected(mdoc, expected)


def test_mdoc_parsing_minimal(input_data_dir, output_data_dir):
    """Test minimal MDOC with only required fields"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_minimal.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_minimal.json")
    compare_mdoc_to_expected(mdoc, expected)


def test_mdoc_t_section_comma(input_data_dir, output_data_dir):
    """Test parsing comma-separated T section"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_t_section_comma.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_t_comma.json")
    compare_mdoc_to_expected(mdoc, expected)


def test_mdoc_t_section_space(input_data_dir, output_data_dir):
    """Test parsing space-separated T section with multi-word keys"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_t_section_space.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_t_space.json")
    compare_mdoc_to_expected(mdoc, expected)


def test_mdoc_t_section_text(input_data_dir, output_data_dir):
    """Test text-only T section is ignored"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_t_section_text.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_t_text.json")
    compare_mdoc_to_expected(mdoc, expected)


def test_mdoc_value_types(input_data_dir, output_data_dir):
    """Test parsing of different value types (int, float, string, list)"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_value_types.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_value_types.json")
    compare_mdoc_to_expected(mdoc, expected)


def test_mdoc_snake_case_conversion(input_data_dir, output_data_dir):
    """Test that PascalCase keys are converted to snake_case"""
    mdoc = metadata_parsing.parse_mdoc_file(str(input_data_dir / "TS_snake_case.mdoc"))
    expected = load_expected_json(output_data_dir, "expected_mdoc_snake_case.json")
    compare_mdoc_to_expected(mdoc, expected)