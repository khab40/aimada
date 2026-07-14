from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_serverless_builds_use_context_specific_dockerignore_files() -> None:
    build_script = (ROOT / "scripts" / "build-serverless-images.sh").read_text(encoding="utf-8")
    root_ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    endpoint_ignore = (ROOT / "serverless" / "endpoint" / ".dockerignore").read_text(encoding="utf-8")

    assert '"${ROOT_DIR}/serverless/endpoint"' in build_script
    assert '"${ROOT_DIR}"' in build_script
    assert ".env" in root_ignore
    assert "outputs" in root_ignore
    assert "test_*.py" in endpoint_ignore
    assert "endpoint_config*.yaml" in endpoint_ignore


def test_serverless_images_use_distinct_dockerfiles_and_tags() -> None:
    build_script = (ROOT / "scripts" / "build-serverless-images.sh").read_text(encoding="utf-8")

    assert 'serverless/endpoint/Dockerfile"' in build_script
    assert 'serverless/jobs/Dockerfile"' in build_script
    assert 'if [[ "${ENDPOINT_IMAGE}" == "${JOBS_IMAGE}" ]]' in build_script
