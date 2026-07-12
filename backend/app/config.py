from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Market Abuse Detection Arena"
    endpoint_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ENDPOINT_TOKEN", "NEBIUS_ENDPOINT_TOKEN"),
    )
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
    nebius_market_abuse_scenario_url: str | None = Field(
        default=None,
        alias="NEBIUS_MARKET_ABUSE_SCENARIO_URL",
    )
    nebius_orderbook_alert_url: str | None = Field(
        default=None,
        alias="NEBIUS_ORDERBOOK_ALERT_URL",
    )
    nebius_investigation_report_url: str | None = Field(
        default=None,
        alias="NEBIUS_INVESTIGATION_REPORT_URL",
    )
    nebius_investigation_team_url: str | None = Field(
        default=None,
        alias="NEBIUS_INVESTIGATION_TEAM_URL",
    )
    nebius_endpoint_mode: str = Field(default="mock", alias="NEBIUS_ENDPOINT_MODE")
    nebius_job_image: str = Field(
        default="ghcr.io/khab40/ai-market-abuse-detection-arena-jobs:latest",
        alias="NEBIUS_JOB_IMAGE",
    )
    nebius_subnet_id: str | None = Field(default=None, alias="NEBIUS_SUBNET_ID")
    nebius_parent_id: str | None = Field(default=None, alias="NEBIUS_PARENT_ID")
    nebius_volume: str | None = Field(default=None, alias="NEBIUS_VOLUME")
    nebius_job_output_volume: str | None = Field(default=None, alias="NEBIUS_JOB_OUTPUT_VOLUME")
    nebius_job_output_uri: str | None = Field(default=None, alias="NEBIUS_JOB_OUTPUT_URI")
    nebius_object_storage_endpoint_url: str | None = Field(
        default=None,
        alias="NEBIUS_OBJECT_STORAGE_ENDPOINT_URL",
    )
    nebius_object_storage_access_key_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID"),
    )
    nebius_object_storage_secret_access_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY"),
    )
    nebius_object_storage_session_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NEBIUS_OBJECT_STORAGE_SESSION_TOKEN", "AWS_SESSION_TOKEN"),
    )
    nebius_object_storage_region: str = Field(
        default="eu-north1",
        validation_alias=AliasChoices("NEBIUS_OBJECT_STORAGE_REGION", "AWS_DEFAULT_REGION"),
    )
    nebius_job_submit_command_template: str | None = Field(
        default=None,
        alias="NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE",
    )
    nebius_job_status_command_template: str | None = Field(
        default=None,
        alias="NEBIUS_JOB_STATUS_COMMAND_TEMPLATE",
    )
    nebius_job_logs_command_template: str | None = Field(
        default=None,
        alias="NEBIUS_JOB_LOGS_COMMAND_TEMPLATE",
    )
    nebius_job_artifacts_command_template: str | None = Field(
        default=None,
        alias="NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE",
    )
    nebius_health_timeout_seconds: float = Field(
        default=0.5,
        ge=0.05,
        le=5.0,
        alias="NEBIUS_HEALTH_TIMEOUT_SECONDS",
    )
    nebius_local_tournament_scenario_limit: int = Field(
        default=24,
        ge=1,
        le=200,
        alias="NEBIUS_LOCAL_TOURNAMENT_SCENARIO_LIMIT",
    )
    arena_output_dir: Path = Field(default=Path("../outputs"), alias="ARENA_OUTPUT_DIR")
    arena_data_retention_days: int = Field(default=1, ge=1, le=3650, alias="ARENA_DATA_RETENTION_DAYS")
    arena_sample_data_dir: Path = Field(default=Path("../data/sample"), alias="ARENA_SAMPLE_DATA_DIR")
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str | None = Field(default=None, alias="GOOGLE_REDIRECT_URI")
    enable_google_auth: bool = Field(default=False, alias="ENABLE_GOOGLE_AUTH")
    enable_advanced_attack_controls: bool = Field(default=False, alias="ENABLE_ADVANCED_ATTACK_CONTROLS")
    enable_legacy_pages: bool = Field(default=False, alias="ENABLE_LEGACY_PAGES")
    aimada_jwt_secret: str = Field(default="dev-only-change-me", alias="AIMADA_JWT_SECRET")
    aimada_jwt_issuer: str = Field(default="ai-market-abuse-detection-arena", alias="AIMADA_JWT_ISSUER")
    aimada_jwt_expires_in_seconds: int = Field(default=43_200, ge=300, le=2_592_000, alias="AIMADA_JWT_EXPIRES_IN_SECONDS")
    arena_agent_count: int = Field(default=200, ge=1, le=1000, alias="ARENA_AGENT_COUNT")
    arena_agent_decision_timeout_seconds: float = Field(
        default=0.05,
        ge=0.001,
        le=1.0,
        alias="ARENA_AGENT_DECISION_TIMEOUT_SECONDS",
    )
    arena_remote_agent_urls: str = Field(default="", alias="ARENA_REMOTE_AGENT_URLS")
    arena_remote_agent_timeout_seconds: float = Field(
        default=0.05,
        ge=0.001,
        le=2.0,
        alias="ARENA_REMOTE_AGENT_TIMEOUT_SECONDS",
    )
    arena_baseline_liquidity_levels: int = Field(
        default=12,
        ge=0,
        le=100,
        alias="ARENA_BASELINE_LIQUIDITY_LEVELS",
    )
    arena_baseline_liquidity_base_size: float = Field(
        default=1.5,
        ge=0.0,
        le=1_000.0,
        alias="ARENA_BASELINE_LIQUIDITY_BASE_SIZE",
    )
    arena_baseline_liquidity_tick_size: float = Field(
        default=1.0,
        gt=0.0,
        le=1_000.0,
        alias="ARENA_BASELINE_LIQUIDITY_TICK_SIZE",
    )
    arena_baseline_liquidity_reference_price: float = Field(
        default=68_125.0,
        gt=0.0,
        alias="ARENA_BASELINE_LIQUIDITY_REFERENCE_PRICE",
    )
    arena_max_agent_quote_size: float = Field(
        default=25.0,
        ge=0.0,
        le=1_000.0,
        alias="ARENA_MAX_AGENT_QUOTE_SIZE",
    )
    arena_tick_history_interval: int = Field(
        default=10,
        ge=1,
        le=10_000,
        alias="ARENA_TICK_HISTORY_INTERVAL",
    )
    arena_persist_all_events: bool = Field(default=False, alias="ARENA_PERSIST_ALL_EVENTS")
    cors_allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
        alias="CORS_ALLOWED_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def remote_agent_url_list(self) -> list[str]:
        return [url.strip() for url in self.arena_remote_agent_urls.split(",") if url.strip()]

    @property
    def cors_allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def nebius_explain_endpoint_url(self) -> str | None:
        return self.nebius_incident_explainer_url or self.nebius_endpoint_url("/explain-event")

    @property
    def nebius_scenario_endpoint_url(self) -> str | None:
        return self.nebius_scenario_generator_url or self.nebius_endpoint_url("/generate-scenario")

    @property
    def nebius_market_abuse_scenario_endpoint_url(self) -> str | None:
        return self.nebius_market_abuse_scenario_url or self.nebius_endpoint_url("/generate-market-abuse-scenario")

    @property
    def nebius_orderbook_alert_endpoint_url(self) -> str | None:
        return self.nebius_orderbook_alert_url or self.nebius_endpoint_url("/orderbook-alert")

    @property
    def nebius_investigation_report_endpoint_url(self) -> str | None:
        return self.nebius_investigation_report_url or self.nebius_endpoint_url("/investigation-report")

    @property
    def nebius_investigation_team_endpoint_url(self) -> str | None:
        return self.nebius_investigation_team_url or self.nebius_endpoint_url("/investigation-team")

    def nebius_endpoint_url(self, path: str) -> str | None:
        if not self.nebius_endpoint_base_url:
            return None
        return f"{self.nebius_endpoint_base_url.rstrip('/')}/{path.lstrip('/')}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
