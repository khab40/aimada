import sqlite3
from pathlib import Path
from typing import Any


class AuthStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def upsert_google_user(
        self,
        *,
        google_id: str,
        email: str,
        name: str,
        avatar_url: str | None,
        now: str,
        user_id: str,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO users (id, email, name, avatar_url, google_id, auth_provider, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'google', ?, ?)
                    """,
                    (user_id, email, name, avatar_url, google_id, now, now),
                )
            else:
                user_id = str(existing["id"])
                conn.execute(
                    """
                    UPDATE users
                    SET email = ?, name = ?, avatar_url = ?, updated_at = ?
                    WHERE google_id = ?
                    """,
                    (email, name, avatar_url, now, google_id),
                )
            row = conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
        return _user_from_row(row)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user_from_row(row) if row is not None else None

    def get_user_by_google_id(self, google_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
        return _user_from_row(row) if row is not None else None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    avatar_url TEXT,
                    google_id TEXT NOT NULL UNIQUE,
                    auth_provider TEXT NOT NULL CHECK (auth_provider = 'google'),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_google_id ON users (google_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")


def _user_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    return {
        **data,
        "user_id": data["id"],
        "provider": data["auth_provider"],
        "provider_mode": "google_verified",
        "google_subject": data["google_id"],
    }
