import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RetentionCleanupResult:
    deleted_files: int
    deleted_dirs: int
    freed_bytes: int
    retention_days: int


def cleanup_output_data(output_dir: Path, retention_days: int) -> RetentionCleanupResult:
    root = output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - max(1, retention_days) * 24 * 60 * 60
    deleted_files = 0
    deleted_dirs = 0
    freed_bytes = 0

    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name == ".gitkeep":
            continue
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        if stat.st_mtime >= cutoff:
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        deleted_files += 1
        freed_bytes += stat.st_size

    directories = sorted((path for path in root.rglob("*") if path.is_dir() and not path.is_symlink()), key=lambda item: len(item.parts), reverse=True)
    for path in directories:
        try:
            path.rmdir()
        except OSError:
            continue
        deleted_dirs += 1

    return RetentionCleanupResult(
        deleted_files=deleted_files,
        deleted_dirs=deleted_dirs,
        freed_bytes=freed_bytes,
        retention_days=max(1, retention_days),
    )
