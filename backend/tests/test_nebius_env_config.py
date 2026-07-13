import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from app.config import Settings
from app.nebius.client import _job_artifact_collection_configured


def test_backend_settings_reads_endpoint_token(monkeypatch: Any) -> None:
    monkeypatch.setenv("ENDPOINT_TOKEN", "endpoint-token")

    settings = Settings(_env_file=None)

    assert settings.endpoint_token == "endpoint-token"


def test_backend_settings_reads_legacy_nebius_endpoint_token(monkeypatch: Any) -> None:
    monkeypatch.delenv("ENDPOINT_TOKEN", raising=False)
    monkeypatch.setenv("NEBIUS_ENDPOINT_TOKEN", "legacy-endpoint-token")

    settings = Settings(_env_file=None)

    assert settings.endpoint_token == "legacy-endpoint-token"


def test_backend_settings_has_no_model_gateway_config() -> None:
    settings = Settings(_env_file=None)

    assert not hasattr(settings, "nebius_base_url")
    assert not hasattr(settings, "nebius_model")


def test_demo_surface_flags_default_to_reduced_demo_mode(monkeypatch: Any) -> None:
    monkeypatch.delenv("ENABLE_GOOGLE_AUTH", raising=False)
    monkeypatch.delenv("ENABLE_ADVANCED_ATTACK_CONTROLS", raising=False)
    monkeypatch.delenv("ENABLE_LEGACY_PAGES", raising=False)
    settings = Settings(_env_file=None)

    assert settings.enable_google_auth is False
    assert settings.enable_advanced_attack_controls is False
    assert settings.enable_legacy_pages is False


def test_backend_settings_default_to_lean_local_runtime(monkeypatch: Any) -> None:
    monkeypatch.delenv("ARENA_REMOTE_AGENT_URLS", raising=False)
    monkeypatch.delenv("ARENA_DATA_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("NEBIUS_HEALTH_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("NEBIUS_LOCAL_TOURNAMENT_SCENARIO_LIMIT", raising=False)
    monkeypatch.delenv("ARENA_TICK_HISTORY_INTERVAL", raising=False)
    monkeypatch.delenv("ARENA_PERSIST_ALL_EVENTS", raising=False)
    settings = Settings(_env_file=None)

    assert settings.arena_remote_agent_urls == ""
    assert settings.arena_data_retention_days == 1
    assert settings.nebius_health_timeout_seconds == 0.5
    assert settings.nebius_local_tournament_scenario_limit == 24
    assert settings.arena_tick_history_interval == 10
    assert settings.arena_persist_all_events is False


def test_backend_settings_derives_investigation_team_endpoint_from_base_url(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_BASE_URL", "https://endpoint.example")
    monkeypatch.delenv("NEBIUS_INVESTIGATION_TEAM_URL", raising=False)
    settings = Settings(_env_file=None)

    assert settings.nebius_investigation_team_endpoint_url == "https://endpoint.example/investigation-team"


def test_s3_artifact_status_requires_credentials_forwarded_to_job() -> None:
    base = {
        "_env_file": None,
        "NEBIUS_JOB_OUTPUT_URI": "s3://aimada-artifacts/aimada",
        "NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID": "access-key",
        "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY": "secret-key",
    }

    missing_forwarder = Settings(
        **base,
        NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE="nebius ai job create --args {job_args}",
    )
    configured = Settings(
        **base,
        NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE="nebius ai job create --args {job_args} {object_storage_env_args}",
    )

    assert _job_artifact_collection_configured(missing_forwarder) is False
    assert _job_artifact_collection_configured(configured) is True


def test_serverless_endpoint_local_vllm_base_url_uses_explicit_value(monkeypatch: Any) -> None:
    endpoint = _load_endpoint_module()
    monkeypatch.setenv("LOCAL_VLLM_BASE_URL", "http://127.0.0.1:8001/v1")

    assert endpoint._local_vllm_base_url() == "http://127.0.0.1:8001/v1"


def test_serverless_endpoint_local_vllm_base_url_uses_host_and_port(monkeypatch: Any) -> None:
    endpoint = _load_endpoint_module()
    monkeypatch.delenv("LOCAL_VLLM_BASE_URL", raising=False)
    monkeypatch.setenv("LOCAL_VLLM_HOST", "127.0.0.1")
    monkeypatch.setenv("LOCAL_VLLM_PORT", "8001")

    assert endpoint._local_vllm_base_url() == "http://127.0.0.1:8001/v1"


def _load_endpoint_module() -> ModuleType:
    endpoint_dir = Path(__file__).resolve().parents[2] / "serverless" / "endpoint"
    module_path = endpoint_dir / "app.py"
    module_name = "serverless_endpoint_app_for_tests"
    sys.path.insert(0, str(endpoint_dir))
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"could not load endpoint module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(endpoint_dir))
