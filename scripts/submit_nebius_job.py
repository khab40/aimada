import argparse
import json
import os
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the smart attack/detect batch as a Nebius Serverless AI Job.")
    parser.add_argument("--image", default=os.environ.get("NEBIUS_JOB_IMAGE", "ghcr.io/your-org/ai-market-abuse-detection-arena-jobs:latest"))
    parser.add_argument("--name", default=os.environ.get("NEBIUS_JOB_NAME", "market-abuse-smart-batch"))
    parser.add_argument("--runs", type=int, default=int(os.environ.get("NEBIUS_JOB_RUNS", "1000")))
    parser.add_argument("--batch-size", type=int, default=int(os.environ.get("NEBIUS_JOB_BATCH_SIZE", "100")))
    parser.add_argument("--subnet-id", default=os.environ.get("NEBIUS_SUBNET_ID"))
    parser.add_argument("--parent-id", default=os.environ.get("NEBIUS_PARENT_ID"))
    parser.add_argument("--platform", default=os.environ.get("NEBIUS_JOB_PLATFORM", "cpu-d3"))
    parser.add_argument("--preset", default=os.environ.get("NEBIUS_JOB_PRESET", "4vcpu-16gb"))
    parser.add_argument("--timeout", default=os.environ.get("NEBIUS_JOB_TIMEOUT", "1h"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.subnet_id:
        raise SystemExit("NEBIUS_SUBNET_ID or --subnet-id is required")

    command = [
        "nebius",
        "ai",
        "job",
        "create",
        "--name",
        args.name,
        "--image",
        args.image,
        "--container-command",
        "python",
        "--args",
        f"/job/serverless/jobs/run_batch_experiments.py --runs {args.runs} --batch-size {args.batch_size} --output /job/outputs/serverless-batch",
        "--platform",
        args.platform,
        "--preset",
        args.preset,
        "--timeout",
        args.timeout,
        "--subnet-id",
        args.subnet_id,
        "--restart-policy",
        "never",
        "--format",
        "json",
    ]
    if args.parent_id:
        command.extend(["--parent-id", args.parent_id])
    if os.environ.get("NEBIUS_VOLUME"):
        command.extend(["--volume", os.environ["NEBIUS_VOLUME"]])

    if args.dry_run:
        print(json.dumps({"command": command}, indent=2))
        return

    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    if completed.returncode != 0:
        raise SystemExit(completed.stderr)
    Path("outputs/nebius").mkdir(parents=True, exist_ok=True)
    Path("outputs/nebius/latest_job_create.json").write_text(completed.stdout, encoding="utf-8")
    print(completed.stdout)


if __name__ == "__main__":
    main()
