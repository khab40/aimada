from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Nebius Market Abuse Arena"
    nebius_api_key: str | None = Field(default=None, alias="NEBIUS_API_KEY")
    nebius_explain_endpoint_url: str = Field(
        default="http://localhost:9000",
        alias="NEBIUS_EXPLAIN_ENDPOINT_URL",
    )
    arena_output_dir: Path = Field(default=Path("../outputs"), alias="ARENA_OUTPUT_DIR")
    arena_sample_data_dir: Path = Field(default=Path("../data/sample"), alias="ARENA_SAMPLE_DATA_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
