import argparse
import json
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


def load_config(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)

    config: dict[str, object] = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and current_list_key:
            config.setdefault(current_list_key, [])
            assert isinstance(config[current_list_key], list)
            config[current_list_key].append(line[2:])
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            config[key] = []
            current_list_key = key
        elif value.isdigit():
            config[key] = int(value)
            current_list_key = None
        else:
            config[key] = value
            current_list_key = None
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run synthetic detector benchmark.")
    parser.add_argument("--config", type=Path, default=Path("job_config.example.yaml"))
    args = parser.parse_args()

    config = load_config(args.config)
    run_count = int(config.get("run_count", 100))
    scenarios = config.get("scenarios", [])
    result = {
        "run_count": run_count,
        "scenarios": scenarios,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "status": "scaffold",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
