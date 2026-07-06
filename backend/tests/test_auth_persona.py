from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import routes_auth
from app.api.routes_auth import GoogleCompleteRequest, SessionSaveRequest, google_complete, logout, me
from app.arena.engine import SimulationEngine
from app.auth.google import GoogleIdentity, GoogleTokenVerificationError
from app.auth.store import AuthStore
from app.storage.local_store import LocalStore


def _request(
    tmp_path: Path,
    *,
    enable_google_auth: bool | None = None,
    google_client_id: str | None = None,
) -> SimpleNamespace:
    store = LocalStore(tmp_path)
    settings = SimpleNamespace(
        aimada_jwt_expires_in_seconds=3600,
        aimada_jwt_issuer="test-issuer",
        aimada_jwt_secret="test-secret",
        google_client_id=google_client_id,
        google_client_secret="google-secret" if google_client_id else None,
        google_redirect_uri="http://localhost:5173/auth/callback",
    )
    if enable_google_auth is not None:
        settings.enable_google_auth = enable_google_auth
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                auth_store=AuthStore(tmp_path / "auth" / "auth.db"),
                settings=settings,
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
    response = logout(SessionSaveRequest(window_hours=24), request, x_aimada_session_id=login.session["session_id"])

    snapshots = request.app.state.store.read_jsonl(f"auth/users/{login.user['user_id']}/history_snapshots.jsonl")

    assert login.user["email"] == "player@example.com"
    assert login.user["auth_provider"] == "google"
    assert login.access_token
    assert login.token_type == "bearer"
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
    logout(SessionSaveRequest(window_hours=24), request, x_aimada_session_id=first_login.session["session_id"])

    second_login = google_complete(
        GoogleCompleteRequest(email="player@example.com", name="Player One", role="observer"),
        request,
    )

    assert second_login.restored_history is not None
    assert second_login.restored_history["history"]["tick_count"] == 1
    assert second_login.session["role"] == "observer"


def test_verified_google_login_stores_user_and_returns_app_jwt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path, google_client_id="client-id.apps.googleusercontent.com")

    def fake_verify(id_token: str, *, client_id: str) -> GoogleIdentity:
        assert id_token == "google-id-token"
        assert client_id == "client-id.apps.googleusercontent.com"
        return GoogleIdentity(
            google_id="google-sub-123",
            email="verified@example.com",
            name="Verified User",
            avatar_url="https://example.com/avatar.png",
        )

    monkeypatch.setattr(routes_auth, "verify_google_id_token", fake_verify)

    login = google_complete(GoogleCompleteRequest(id_token="google-id-token", role="judge"), request)
    stored = request.app.state.auth_store.get_user_by_google_id("google-sub-123")
    current = me(request, authorization=f"Bearer {login.access_token}")

    assert stored is not None
    assert stored["id"] == login.user["id"]
    assert stored["email"] == "verified@example.com"
    assert stored["name"] == "Verified User"
    assert stored["avatar_url"] == "https://example.com/avatar.png"
    assert stored["google_id"] == "google-sub-123"
    assert stored["auth_provider"] == "google"
    assert login.user["google_id"] == "google-sub-123"
    assert login.session["role"] == "judge"
    assert login.access_token and login.access_token != "google-id-token"
    assert current.user["email"] == "verified@example.com"


def test_google_authorization_code_popup_flow_uses_explicit_redirect_uri(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path, google_client_id="client-id.apps.googleusercontent.com")

    def fake_exchange(*, code: str, client_id: str, client_secret: str, redirect_uri: str | None = None) -> str:
        assert code == "popup-code"
        assert client_id == "client-id.apps.googleusercontent.com"
        assert client_secret == "google-secret"
        assert redirect_uri == "http://localhost:5173"
        return "exchanged-google-id-token"

    def fake_verify(id_token: str, *, client_id: str) -> GoogleIdentity:
        assert id_token == "exchanged-google-id-token"
        assert client_id == "client-id.apps.googleusercontent.com"
        return GoogleIdentity(
            google_id="google-sub-code",
            email="code@example.com",
            name="Code User",
            avatar_url=None,
        )

    monkeypatch.setattr(routes_auth, "exchange_code_for_id_token", fake_exchange)
    monkeypatch.setattr(routes_auth, "verify_google_id_token", fake_verify)

    login = google_complete(
        GoogleCompleteRequest(authorization_code="popup-code", redirect_uri="http://localhost:5173", role="defender"),
        request,
    )

    assert login.user["google_id"] == "google-sub-code"
    assert login.user["email"] == "code@example.com"
    assert login.session["role"] == "defender"


def test_configured_google_login_returns_verification_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path, google_client_id="client-id.apps.googleusercontent.com")

    def fake_verify(id_token: str, *, client_id: str) -> GoogleIdentity:
        raise GoogleTokenVerificationError("Wrong recipient")

    monkeypatch.setattr(routes_auth, "verify_google_id_token", fake_verify)

    with pytest.raises(HTTPException) as exc:
        google_complete(GoogleCompleteRequest(id_token="google-id-token", role="observer"), request)

    assert exc.value.status_code == 401
    assert "Wrong recipient" in str(exc.value.detail)


def test_configured_google_login_requires_google_token_or_code(tmp_path: Path) -> None:
    request = _request(tmp_path, google_client_id="client-id.apps.googleusercontent.com")

    with pytest.raises(HTTPException) as exc:
        google_complete(GoogleCompleteRequest(role="observer"), request)

    assert exc.value.status_code == 400
    assert "id_token" in str(exc.value.detail)


def test_explicit_google_auth_requires_client_id(tmp_path: Path) -> None:
    request = _request(tmp_path, enable_google_auth=True)

    with pytest.raises(HTTPException) as exc:
        google_complete(GoogleCompleteRequest(email="player@example.com", role="observer"), request)

    assert exc.value.status_code == 500
    assert "GOOGLE_CLIENT_ID" in str(exc.value.detail)
