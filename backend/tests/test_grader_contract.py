from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_public_grader_command_is_documented_and_credential_free() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    script = (ROOT / "scripts" / "grader-smoke.sh").read_text(encoding="utf-8")

    assert "grader-smoke:" in makefile
    assert "make grader-smoke" in readme
    assert "NEBIUS_ENDPOINT_MODE=mock" in script
    assert "NEBIUS_EVIDENCE_ARCHIVE_ENABLED=false" in script
    assert script.count("printf '%s\\n' GRADER_OK") == 1


def test_default_branch_and_docker_context_contracts() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    root_ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    frontend_ignore = (ROOT / "frontend" / ".dockerignore").read_text(encoding="utf-8")

    assert "branches: [main]" in workflow
    assert "master" not in workflow
    assert root_ignore.splitlines()[3] == "**"
    assert "backend/**" in root_ignore
    assert "!backend/app/**" in root_ignore
    assert "!assets/" not in root_ignore
    assert frontend_ignore.splitlines()[1] == "**"
    assert "!src/**" in frontend_ignore
