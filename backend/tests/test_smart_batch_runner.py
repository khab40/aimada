import sys
from pathlib import Path
from typing import Any

from app.nebius import smart_batch_runner


def test_batch_runner_uses_backend_uv_project_when_available(monkeypatch: Any, tmp_path: Path) -> None:
    repo_root = tmp_path
    backend = repo_root / "backend"
    backend.mkdir()
    (backend / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")

    monkeypatch.setattr(smart_batch_runner.shutil, "which", lambda name: "/usr/local/bin/uv" if name == "uv" else None)

    assert smart_batch_runner._batch_python_command(repo_root) == [
        "/usr/local/bin/uv",
        "run",
        "--project",
        str(backend),
        "python",
    ]


def test_batch_runner_falls_back_to_current_python_without_uv(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(smart_batch_runner.shutil, "which", lambda name: None)

    assert smart_batch_runner._batch_python_command(tmp_path) == [sys.executable]
