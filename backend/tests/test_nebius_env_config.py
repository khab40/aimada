import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from app.config import Settings


def test_backend_settings_prefers_new_nebius_base_url_and_model(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_BASE_URL", "https://new.example/v1/")
    monkeypatch.setenv("NEBIUS_AI_STUDIO_BASE_URL", "https://old.example/v1/")
    monkeypatch.setenv("NEBIUS_MODEL", "new-model")
    monkeypatch.setenv("NEBIUS_AI_MODEL", "old-model")

    settings = Settings(_env_file=None)

    assert settings.nebius_base_url == "https://new.example/v1/"
    assert settings.nebius_model == "new-model"


def test_backend_settings_accepts_old_nebius_aliases(monkeypatch: Any) -> None:
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)
    monkeypatch.delenv("NEBIUS_MODEL", raising=False)
    monkeypatch.setenv("NEBIUS_AI_STUDIO_BASE_URL", "https://old.example/v1/")
    monkeypatch.setenv("NEBIUS_AI_MODEL", "old-model")

    settings = Settings(_env_file=None)

    assert settings.nebius_base_url == "https://old.example/v1/"
    assert settings.nebius_model == "old-model"


def test_demo_surface_flags_default_to_reduced_demo_mode(monkeypatch: Any) -> None:
    monkeypatch.delenv("ENABLE_GOOGLE_AUTH", raising=False)
    monkeypatch.delenv("ENABLE_ADVANCED_ATTACK_CONTROLS", raising=False)
    monkeypatch.delenv("ENABLE_LEGACY_PAGES", raising=False)
    settings = Settings(_env_file=None)

    assert settings.enable_google_auth is False
    assert settings.enable_advanced_attack_controls is False
    assert settings.enable_legacy_pages is False


def test_backend_settings_derives_investigation_team_endpoint_from_base_url(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_BASE_URL", "https://endpoint.example")
    monkeypatch.delenv("NEBIUS_INVESTIGATION_TEAM_URL", raising=False)
    settings = Settings(_env_file=None)

    assert settings.nebius_investigation_team_endpoint_url == "https://endpoint.example/investigation-team"


def test_serverless_endpoint_prefers_new_nebius_env_names(monkeypatch: Any) -> None:
    endpoint = _load_endpoint_module()
    monkeypatch.setenv("NEBIUS_BASE_URL", "https://new.example/v1/")
    monkeypatch.setenv("NEBIUS_AI_STUDIO_BASE_URL", "https://old.example/v1/")
    monkeypatch.setenv("NEBIUS_MODEL", "new-model")
    monkeypatch.setenv("NEBIUS_AI_MODEL", "old-model")

    assert endpoint._nebius_base_url() == "https://new.example/v1/"
    assert endpoint._nebius_model() == "new-model"


def test_serverless_endpoint_accepts_old_nebius_env_aliases(monkeypatch: Any) -> None:
    endpoint = _load_endpoint_module()
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)
    monkeypatch.delenv("NEBIUS_MODEL", raising=False)
    monkeypatch.setenv("NEBIUS_AI_STUDIO_BASE_URL", "https://old.example/v1/")
    monkeypatch.setenv("NEBIUS_AI_MODEL", "old-model")

    assert endpoint._nebius_base_url() == "https://old.example/v1/"
    assert endpoint._nebius_model() == "old-model"


def test_serverless_endpoint_uses_tokenfactory_default(monkeypatch: Any) -> None:
    endpoint = _load_endpoint_module()
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)
    monkeypatch.delenv("NEBIUS_AI_STUDIO_BASE_URL", raising=False)

    assert endpoint._nebius_base_url() == "https://api.tokenfactory.nebius.com/v1/"


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
