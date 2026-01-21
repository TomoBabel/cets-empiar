import os
import logging

from pathlib import Path
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger("__main__." + __name__)


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).parents[1] / ".env"), 
        ],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    default_empiar_definition_dir: Path = Field(Path(__file__).parents[1] / "definition_files/empiar")
    default_cets_output_dir: Path = Field(Path(__file__).parents[1] / "output_data/CETS")
    default_ro_crate_output_dir: Path = Field(Path(__file__).parents[1] / "output_data/RO_Crate")
    default_cache_dir: Path = Path.home() / ".cache" / "cets-empiar"


def get_settings():
    return Settings() 
