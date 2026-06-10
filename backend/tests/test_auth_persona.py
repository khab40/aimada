from pathlib import Path
from types import SimpleNamespace

from app.api.routes_auth import GoogleCompleteRequest, SessionSaveRequest, google_complete, logout
from app.arena.engine import SimulationEngine
from app.storage.local_store import LocalStore


def _request(tmp_path: Path) -> SimpleNamespace:
    store = LocalStore(tmp_path)
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                store=store,
                simulation=SimulationEngine(store=store),
            )
        )
    )


def test_google_stub_login_creates_session_and_logout_saves_history(tmp_path: Path) -> None:
    request = _request(tmp_path)
    request.app.state.simulation.step()

    login = google_complete(
        GoogleCompleteRequest(email="player@example.com", name="Player One", role="attacker"),
        request,
    )
    response = logout(SessionSaveRequest(window_hours=24), request, x_nmaa_session_id=login.session["session_id"])

    snapshots = request.app.state.store.read_jsonl(f"auth/users/{login.user['user_id']}/history_snapshots.jsonl")

    assert login.user["email"] == "player@example.com"
    assert login.session["role"] == "attacker"
    assert response.saved is True
    assert snapshots
    assert snapshots[-1]["history"]["tick_count"] == 1


def test_login_restores_latest_saved_history(tmp_path: Path) -> None:
    request = _request(tmp_path)
    request.app.state.simulation.step()
    first_login = google_complete(
        GoogleCompleteRequest(email="player@example.com", name="Player One", role="defender"),
        request,
    )
    logout(SessionSaveRequest(window_hours=24), request, x_nmaa_session_id=first_login.session["session_id"])

    second_login = google_complete(
        GoogleCompleteRequest(email="player@example.com", name="Player One", role="observer"),
        request,
    )

    assert second_login.restored_history is not None
    assert second_login.restored_history["history"]["tick_count"] == 1
    assert second_login.session["role"] == "observer"
