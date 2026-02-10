import pytest
import shutil
from pathlib import Path

from cets_empiar.settings import get_settings

@pytest.fixture
def input_data_dir():
    """Return path to input data directory"""
    return Path(__file__).parent / "input_data"


@pytest.fixture
def output_data_dir():
    """Return path to output data directory"""
    return Path(__file__).parent / "output_data"


@pytest.fixture(autouse=True)
def cleanup_test_cache():
    """Clean up cached mdoc files before each test"""
    
    cache_dir = get_settings().default_cache_dir
    test_entry_cache = cache_dir / "EMPIAR-99999"

    if test_entry_cache.exists():
        shutil.rmtree(test_entry_cache)
    
    yield 
    