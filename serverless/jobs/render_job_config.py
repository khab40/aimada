import argparse
from pathlib import Path
from typing import Any

import yaml


DEFAULT_TEMPLATE_PATH = Path(__file__).with_name("nebius_job_config.yaml")
DEFAULT_OUTPUT_ROOT = Path("outputs") / "experiments"
DEFAULT_JOB_OUTPUT_PREFIX = "/job/outputs/experiments"


def render_job_config(
    *,
    experiment_id: str,
    runs: int,
    batch_size: int,
    scenarios: list[str],
    random_seed: int,
    image: str,
    output_dir: str,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
    rendered_path: Path | None = None,
) -> Path:
    if not experiment_id.strip():
        raise ValueError("experiment_id is required")
    if runs < 1:
        raise ValueError("runs must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    clean_scenarios = [scenario.strip() for scenario in scenarios if scenario.strip()]
    if not clean_scenarios:
        raise ValueError("at least one scenario is required")
    if not image.strip():
        raise ValueError("image is required")
    if not output_dir.strip():
        raise ValueError("output_dir is required")

    config = _load_template(template_path)
    repository, tag = _split_image(image.strip())
    scenario_arg = ",".join(clean_scenarios)

    config["args"] = (
        f"/job/serverless/jobs/run_batch_experiments.py --runs {runs} "
        f"--batch-size {batch_size} --scenarios {scenario_arg} "
        f"--random-seed {random_seed} --output {output_dir}"
    )
    config["image"] = {"repository": repository, "tag": tag}
    config["scenarios"] = clean_scenarios
    config.setdefault("outputs", {})["directory"] = output_dir

    output_path = (rendered_path or DEFAULT_OUTPUT_ROOT / experiment_id / "nebius_job_config.rendered.yaml").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return output_path


def _load_template(template_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"job config template is not a YAML object: {template_path}")
    return config


def _split_image(image: str) -> tuple[str, str]:
    last_slash = image.rfind("/")
    last_colon = image.rfind(":")
    if last_colon > last_slash:
        repository = image[:last_colon]
        tag = image[last_colon + 1 :] or "latest"
        return repository, tag
    return image, "latest"


def _parse_scenarios(value: str) -> list[str]:
    return [scenario.strip() for scenario in value.split(",") if scenario.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Nebius Serverless Job config for one experiment.")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--runs", required=True, type=int)
    parser.add_argument("--batch-size", required=True, type=int)
    parser.add_argument("--scenarios", required=True)
    parser.add_argument("--random-seed", required=True, type=int)
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory inside the Nebius job container.",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE_PATH)
    parser.add_argument("--rendered-path", type=Path, default=None)
    args = parser.parse_args()

    job_output_dir = args.output_dir or f"{DEFAULT_JOB_OUTPUT_PREFIX}/{args.experiment_id}/local-batch"
    rendered_path = render_job_config(
        experiment_id=args.experiment_id,
        runs=args.runs,
        batch_size=args.batch_size,
        scenarios=_parse_scenarios(args.scenarios),
        random_seed=args.random_seed,
        image=args.image,
        output_dir=job_output_dir,
        template_path=args.template,
        rendered_path=args.rendered_path,
    )
    print(rendered_path)


if __name__ == "__main__":
    main()
