import json
from collections import deque
from pathlib import Path
from typing import Any, Iterator


class LocalStore:
    _TAIL_BLOCK_SIZE = 64 * 1024

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

    def read_json(self, name: str) -> object | None:
        path = self.output_dir / name
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_jsonl(self, name: str, limit: int | None = None) -> list[dict[str, Any]]:
        if limit is not None and limit <= 0:
            return []
        rows = self.iter_jsonl(name, limit=limit)
        return list(rows)

    def iter_jsonl(self, name: str, limit: int | None = None) -> Iterator[dict[str, Any]]:
        path = self.output_dir / name
        if not path.exists():
            return
        if limit is not None and limit <= 0:
            return
        if limit is not None:
            yield from self._iter_jsonl_tail(path, limit)
            return
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                decoded = json.loads(line)
                if isinstance(decoded, dict):
                    yield decoded

    def _iter_jsonl_tail(self, path: Path, limit: int) -> Iterator[dict[str, Any]]:
        if limit <= 0:
            return
        with path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            chunks: deque[bytes] = deque()
            line_count = 0
            while position > 0 and line_count <= limit:
                read_size = min(self._TAIL_BLOCK_SIZE, position)
                position -= read_size
                handle.seek(position)
                chunk = handle.read(read_size)
                chunks.appendleft(chunk)
                line_count = b"".join(chunks).count(b"\n")
            data = b"".join(chunks)
        lines = data.splitlines()
        for raw_line in lines[-limit:]:
            line = raw_line.strip()
            if not line:
                continue
            decoded = json.loads(line.decode("utf-8"))
            if isinstance(decoded, dict):
                yield decoded
