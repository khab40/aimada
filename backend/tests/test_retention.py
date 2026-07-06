import os
import time

from app.storage.retention import cleanup_output_data


def test_cleanup_output_data_removes_files_older_than_retention(tmp_path) -> None:
    old_file = tmp_path / "history" / "old.jsonl"
    new_file = tmp_path / "history" / "new.jsonl"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")
    old_timestamp = time.time() - 3 * 24 * 60 * 60
    os.utime(old_file, (old_timestamp, old_timestamp))

    result = cleanup_output_data(tmp_path, retention_days=1)

    assert result.deleted_files == 1
    assert result.freed_bytes == 3
    assert not old_file.exists()
    assert new_file.exists()


def test_cleanup_output_data_removes_empty_old_directories(tmp_path) -> None:
    old_file = tmp_path / "auth" / "users" / "old.json"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("old", encoding="utf-8")
    old_timestamp = time.time() - 3 * 24 * 60 * 60
    os.utime(old_file, (old_timestamp, old_timestamp))

    result = cleanup_output_data(tmp_path, retention_days=1)

    assert result.deleted_files == 1
    assert result.deleted_dirs >= 1
    assert not old_file.parent.exists()


def test_cleanup_output_data_preserves_gitkeep(tmp_path) -> None:
    gitkeep = tmp_path / ".gitkeep"
    gitkeep.write_text("", encoding="utf-8")
    old_timestamp = time.time() - 3 * 24 * 60 * 60
    os.utime(gitkeep, (old_timestamp, old_timestamp))

    result = cleanup_output_data(tmp_path, retention_days=1)

    assert result.deleted_files == 0
    assert gitkeep.exists()
