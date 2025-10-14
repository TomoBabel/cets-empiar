from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


env_file = Path(__file__).parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=env_file, extra="allow")
    
    cache_root_dirpath: Path = Path.home() / ".cache" / "cets-empiar"
    
    @field_validator('cache_root_dirpath')
    @classmethod
    def validate_cache_path(cls, v: Path) -> Path:
        """Ensure cache directory can be created."""
        
        v = v.expanduser().resolve()
        
        if v.exists() and not v.is_dir():
            raise ValueError(f"Cache path exists but is not a directory: {v}")
        
        # Check creation
        v.mkdir(parents=True, exist_ok=True)
        
        return v


settings = Settings()
