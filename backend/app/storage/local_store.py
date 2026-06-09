import json
from pathlib import Path
from typing import Any


class LocalStore:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def append_jsonl(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return path

    def write_json(self, name: str, payload: object) -> Path:
        path = self.output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def read_jsonl(self, name: str, limit: int | None = None) -> list[dict[str, Any]]:
        path = self.output_dir / name
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                decoded = json.loads(line)
                if isinstance(decoded, dict):
                    rows.append(decoded)
        if limit is None:
            return rows
        return rows[-limit:]
