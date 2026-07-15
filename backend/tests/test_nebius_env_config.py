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


def test_backend_defaults_to_mock_mode_without_nebius_cloud(monkeypatch: Any) -> None:
    monkeypatch.delenv("NEBIUS_ENDPOINT_MODE", raising=False)
    monkeypatch.delenv("NEBIUS_ENDPOINT_BASE_URL", raising=False)
    monkeypatch.delenv("ENDPOINT_TOKEN", raising=False)
    monkeypatch.delenv("NEBIUS_ENDPOINT_TOKEN", raising=False)

    settings = Settings(_env_file=None)

    assert settings.nebius_endpoint_mode == "mock"
    assert settings.nebius_endpoint_base_url is None
    assert settings.endpoint_token is None


def test_compose_defaults_backend_to_mock_mode() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "NEBIUS_ENDPOINT_MODE: ${NEBIUS_ENDPOINT_MODE:-mock}" in compose


def test_backend_settings_has_no_model_gateway_config() -> None:
    settings = Settings(_env_file=None)

    assert not hasattr(settings, "nebius_base_url")
    assert not hasattr(settings, "nebius_model")


def test_archived_feature_settings_are_not_active() -> None:
    settings = Settings(_env_file=None)

    assert not hasattr(settings, "enable_google_auth")
    assert not hasattr(settings, "enable_advanced_attack_controls")
    assert not hasattr(settings, "enable_legacy_pages")


def test_backend_settings_default_to_lean_local_runtime(monkeypatch: Any) -> None:
    monkeypatch.delenv("ARENA_REMOTE_AGENT_URLS", raising=False)
    monkeypatch.delenv("ARENA_DATA_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("NEBIUS_HEALTH_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("NEBIUS_INFERENCE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("NEBIUS_LOCAL_TOURNAMENT_SCENARIO_LIMIT", raising=False)
    monkeypatch.delenv("ARENA_TICK_HISTORY_INTERVAL", raising=False)
    monkeypatch.delenv("ARENA_PERSIST_ALL_EVENTS", raising=False)
    settings = Settings(_env_file=None)

    assert settings.arena_remote_agent_urls == ""
    assert settings.arena_data_retention_days == 1
    assert settings.nebius_health_timeout_seconds == 0.5
    assert settings.nebius_inference_timeout_seconds == 180.0
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


def test_l40s_endpoint_deployment_is_single_gpu_and_memory_bounded() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    startup = (repo_root / "serverless" / "endpoint" / "start.sh").read_text(encoding="utf-8")
    deployment = (repo_root / "serverless" / "endpoint" / "endpoint_config.yaml").read_text(encoding="utf-8")
    create_script = (repo_root / "scripts" / "create-nebius-ai-endpoint.sh").read_text(encoding="utf-8")

    assert "platform: gpu-l40s-d" in deployment
    assert "preset: 1gpu-16vcpu-96gb" in deployment
    assert 'PLATFORM="${NEBIUS_ENDPOINT_PLATFORM:-gpu-l40s-d}"' in create_script
    assert "Qwen/Qwen2.5-14B-Instruct" in startup
    for flag in (
        "--dtype",
        "--gpu-memory-utilization",
        "--max-model-len",
        "--enable-prefix-caching",
        "--max-num-seqs",
        "--trust-remote-code",
    ):
        assert flag in startup

    weight_gib = 14.7e9 * 2 / 1024**3
    kv_cache_gib = 2 * 48 * 8 * 128 * 2 * 16384 / 1024**3
    l40s_vllm_budget_gib = 48 * 0.90
    assert weight_gib + kv_cache_gib < l40s_vllm_budget_gib
    assert l40s_vllm_budget_gib - weight_gib - kv_cache_gib > 12


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
