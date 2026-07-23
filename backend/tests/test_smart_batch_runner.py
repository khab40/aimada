import subprocess
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


def test_batch_runner_passes_scenario_text_as_one_non_shell_argument(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(smart_batch_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(smart_batch_runner, "read_metrics", lambda _path: [])

    malicious_text = "normal_market; touch /tmp/should-not-exist"
    smart_batch_runner.run_local_smart_batch(
        repo_root=tmp_path,
        output_dir=tmp_path / "output",
        runs=1,
        batch_size=1,
        scenarios=[malicious_text],
    )

    argv = captured["argv"]
    assert argv[argv.index("--scenarios") + 1] == malicious_text
    assert "shell" not in captured["kwargs"]
    assert captured["kwargs"]["cwd"] == tmp_path


def test_batch_runner_does_not_interpolate_shell_metacharacters(monkeypatch: Any, tmp_path: Path) -> None:
    marker = tmp_path / "should-not-exist"
    monkeypatch.setattr(
        smart_batch_runner.subprocess,
        "run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, stdout="", stderr=""),
    )
    monkeypatch.setattr(smart_batch_runner, "read_metrics", lambda _path: [])

    smart_batch_runner.run_local_smart_batch(
        repo_root=tmp_path,
        output_dir=tmp_path / "output",
        runs=1,
        batch_size=1,
        scenarios=[f"normal_market; touch {marker}"],
    )

    assert not marker.exists()
