import argparse
import runpy
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local detector tournament and smart batch eval.")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    tournament = repo / "serverless" / "jobs" / "detector_tournament.py"
    sys.argv = [
        str(tournament),
        "--runs",
        str(args.runs),
        "--scenarios",
        "normal_market,spoofing_like_wall,layering_like,quote_stuffing,liquidity_evaporation",
        "--output",
        str(args.output / "benchmark"),
    ]
    runpy.run_path(str(tournament), run_name="__main__")

    batch = repo / "serverless" / "jobs" / "run_batch_experiments.py"
    sys.argv = [
        str(batch),
        "--runs",
        str(args.runs),
        "--batch-size",
        str(args.batch_size),
        "--output",
        str(args.output / "serverless-batch"),
    ]
    runpy.run_path(str(batch), run_name="__main__")


if __name__ == "__main__":
    main()
