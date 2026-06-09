import argparse
import runpy
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reproducible synthetic market scenarios.")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("outputs/synthetic-dataset"))
    args = parser.parse_args()

    script = Path(__file__).resolve().parents[1] / "serverless" / "jobs" / "synthetic_dataset_factory.py"
    sys.argv = [str(script), "--samples", str(args.samples), "--output", str(args.output)]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
