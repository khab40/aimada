from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from app.storage.history import append_history_artifact, history_window, utc_now
from app.storage.local_store import LocalStore

ArenaRole = Literal["attacker", "defender", "observer", "judge"]

SESSION_HEADER = "X-NMAA-Session-ID"


def user_id_for_google_identity(subject: str | None, email: str | None) -> str:
    stable_key = subject or email or f"anonymous-{uuid4().hex}"
    return f"google-{sha256(stable_key.encode('utf-8')).hexdigest()[:16]}"


def create_session(
    store: LocalStore,
    *,
    email: str,
    name: str,
    role: ArenaRole = "observer",
    google_subject: str | None = None,
    avatar_url: str | None = None,
) -> dict[str, Any]:
    now = utc_now()
    user = {
        "user_id": user_id_for_google_identity(google_subject, email),
        "provider": "google",
        "provider_mode": "stub_until_google_endpoints_are_configured",
        "google_subject": google_subject,
        "email": email,
        "name": name,
        "avatar_url": avatar_url,
        "created_at": now,
    }
    session = {
        "session_id": f"SES-{uuid4().hex[:16].upper()}",
        "user_id": user["user_id"],
        "role": role,
        "created_at": now,
        "last_seen_at": now,
        "active": True,
    }
    store.append_jsonl("auth/users.jsonl", _without_none(user))
    store.append_jsonl("auth/sessions.jsonl", {"event": "login", "created_at": now, "user": _without_none(user), "session": session})
    return {"user": _without_none(user), "session": session}


def find_session(store: LocalStore, session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    for row in reversed(store.read_jsonl("auth/sessions.jsonl", limit=None)):
        session = row.get("session")
        if not isinstance(session, dict) or session.get("session_id") != session_id:
            continue
        if row.get("event") == "logout":
            return None
        user = row.get("user")
        if isinstance(user, dict):
            return {"user": user, "session": session}
    return None


def update_role(store: LocalStore, *, session_id: str, role: ArenaRole) -> dict[str, Any] | None:
    current = find_session(store, session_id)
    if current is None:
        return None
    session = {**current["session"], "role": role, "last_seen_at": utc_now()}
    row = {
        "event": "role_selected",
        "created_at": session["last_seen_at"],
        "user": current["user"],
        "session": session,
    }
    store.append_jsonl("auth/sessions.jsonl", row)
    return {"user": current["user"], "session": session}


def save_session_history(store: LocalStore, *, session_id: str, window_hours: float = 24.0) -> dict[str, Any] | None:
    current = find_session(store, session_id)
    if current is None:
        return None
    user = current["user"]
    session = {**current["session"], "last_seen_at": utc_now()}
    replay = history_window(store, window_hours=window_hours, limit=20_000)
    snapshot = {
        "snapshot_id": f"SNAP-{uuid4().hex[:12].upper()}",
        "created_at": utc_now(),
        "user": user,
        "session": session,
        "history": replay,
    }
    user_path = _user_history_path(str(user["user_id"]))
    store.append_jsonl(f"{user_path}/history_snapshots.jsonl", snapshot)
    store.write_json(f"{user_path}/latest_history.json", snapshot)
    store.append_jsonl("auth/sessions.jsonl", {"event": "history_saved", "created_at": snapshot["created_at"], "user": user, "session": session, "snapshot_id": snapshot["snapshot_id"]})
    append_history_artifact(
        store,
        kind="artifact",
        payload={
            "snapshot_id": snapshot["snapshot_id"],
            "user_id": user["user_id"],
            "tick_count": replay["tick_count"],
            "artifact_count": replay["artifact_count"],
        },
        summary=f"Saved session history for {user.get('email')}",
        created_at=snapshot["created_at"],
        run_id=session["session_id"],
        source="auth_session_save",
        source_path=f"{user_path}/latest_history.json",
    )
    return snapshot


def restore_latest_history(store: LocalStore, *, user_id: str, session_id: str) -> dict[str, Any] | None:
    latest = store.read_json(f"{_user_history_path(user_id)}/latest_history.json")
    if not isinstance(latest, dict):
        return None
    history = latest.get("history")
    if not isinstance(history, dict):
        return latest

    current_artifact_ids = {str(row.get("history_id")) for row in store.read_jsonl("history/artifacts.jsonl", limit=None)}
    current_tick_ids = {str(row.get("history_id")) for row in store.read_jsonl("history/ticks.jsonl", limit=None)}
    restored_artifacts = 0
    restored_ticks = 0
    for row in history.get("artifacts", []):
        if isinstance(row, dict) and str(row.get("history_id")) not in current_artifact_ids:
            store.append_jsonl("history/artifacts.jsonl", {**row, "restored_for_session_id": session_id, "restored_at": utc_now()})
            restored_artifacts += 1
    for row in history.get("ticks", []):
        if isinstance(row, dict) and str(row.get("history_id")) not in current_tick_ids:
            store.append_jsonl("history/ticks.jsonl", {**row, "restored_for_session_id": session_id, "restored_at": utc_now()})
            restored_ticks += 1
    latest["restore"] = {
        "restored_artifacts": restored_artifacts,
        "restored_ticks": restored_ticks,
        "session_id": session_id,
        "restored_at": utc_now(),
    }
    return latest


def close_session(store: LocalStore, *, session_id: str) -> dict[str, Any] | None:
    current = find_session(store, session_id)
    if current is None:
        return None
    session = {**current["session"], "active": False, "last_seen_at": utc_now()}
    store.append_jsonl("auth/sessions.jsonl", {"event": "logout", "created_at": session["last_seen_at"], "user": current["user"], "session": session})
    return {"user": current["user"], "session": session}


def _user_history_path(user_id: str) -> str:
    safe_user_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in user_id)
    return f"auth/users/{safe_user_id}"


def _without_none(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}
