from app.storage.local_store import LocalStore


def test_read_jsonl_limit_returns_tail(tmp_path) -> None:
    store = LocalStore(tmp_path)
    for index in range(100):
        store.append_jsonl("large/events.jsonl", {"index": index})

    rows = store.read_jsonl("large/events.jsonl", limit=3)

    assert [row["index"] for row in rows] == [97, 98, 99]


def test_read_jsonl_zero_limit_returns_empty(tmp_path) -> None:
    store = LocalStore(tmp_path)
    store.append_jsonl("large/events.jsonl", {"index": 1})

    assert store.read_jsonl("large/events.jsonl", limit=0) == []
