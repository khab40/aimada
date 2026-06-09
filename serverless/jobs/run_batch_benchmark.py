from pathlib import Path
import runpy


if __name__ == "__main__":
    runner = Path(__file__).resolve().parent / "run_batch_experiments.py"
    runpy.run_path(str(runner), run_name="__main__")
