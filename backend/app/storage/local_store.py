import json
from pathlib import Path


class LocalStore:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def append_jsonl(self, name: str, payload: dict[str, object]) -> Path:
        path = self.output_dir / name
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return path

    def write_json(self, name: str, payload: object) -> Path:
        path = self.output_dir / name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
