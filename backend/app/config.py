from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Market Abuse Detection Arena"
    nebius_api_key: str | None = Field(default=None, alias="NEBIUS_API_KEY")
    nebius_tenant_id: str | None = Field(default=None, alias="NEBIUS_TENANT_ID")
    nebius_endpoint_base_url: str | None = Field(
        default=None,
        alias="NEBIUS_ENDPOINT_BASE_URL",
    )
    nebius_incident_explainer_url: str | None = Field(
        default=None,
        alias="NEBIUS_INCIDENT_EXPLAINER_URL",
    )
    nebius_scenario_generator_url: str | None = Field(
        default=None,
        alias="NEBIUS_SCENARIO_GENERATOR_URL",
    )
    arena_output_dir: Path = Field(default=Path("../outputs"), alias="ARENA_OUTPUT_DIR")
    arena_sample_data_dir: Path = Field(default=Path("../data/sample"), alias="ARENA_SAMPLE_DATA_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def nebius_explain_endpoint_url(self) -> str | None:
        return self.nebius_incident_explainer_url or self.nebius_endpoint_url("/explain-event")

    @property
    def nebius_scenario_endpoint_url(self) -> str | None:
        return self.nebius_scenario_generator_url or self.nebius_endpoint_url("/generate-scenario")

    def nebius_endpoint_url(self, path: str) -> str | None:
        if not self.nebius_endpoint_base_url:
            return None
        return f"{self.nebius_endpoint_base_url.rstrip('/')}/{path.lstrip('/')}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
