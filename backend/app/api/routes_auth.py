from typing import Any
from urllib import parse

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.google import GoogleIdentity, GoogleOAuthError, GoogleTokenVerificationError, exchange_code_for_id_token, verify_google_id_token
from app.auth.persona import (
    SESSION_HEADER,
    ArenaRole,
    bearer_token_from_authorization,
    close_session,
    create_session,
    find_session,
    find_session_by_jwt,
    restore_latest_history,
    save_session_history,
    update_role,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleAuthConfig(BaseModel):
    mode: str
    configured: bool
    client_id: str | None = None
    authorization_url: str | None = None
    detail: str


class GoogleCompleteRequest(BaseModel):
    id_token: str | None = None
    authorization_code: str | None = None
    code: str | None = None
    redirect_uri: str | None = None
    google_subject: str | None = None
    email: str = "demo.user@example.com"
    name: str = "Demo Google User"
    avatar_url: str | None = None
    role: ArenaRole = "observer"


class RoleUpdateRequest(BaseModel):
    role: ArenaRole


class SessionSaveRequest(BaseModel):
    window_hours: float = Field(default=24.0, ge=0.01, le=24.0)


class AuthSessionResponse(BaseModel):
    user: dict[str, Any]
    session: dict[str, Any]
    restored_history: dict[str, Any] | None = None
    access_token: str | None = None
    token_type: str | None = None


class SessionSaveResponse(BaseModel):
    saved: bool
    snapshot: dict[str, Any] | None = None


@router.get("/google/config", response_model=GoogleAuthConfig)
def google_config(request: Request) -> GoogleAuthConfig:
    settings = _settings(request)
    configured = bool(settings.google_client_id)
    redirect_uri = settings.google_redirect_uri or "http://localhost:5173"
    authorization_url = None
    if configured:
        authorization_url = "https://accounts.google.com/o/oauth2/v2/auth?" + parse.urlencode(
            {
                "client_id": settings.google_client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "select_account",
            }
        )
    return GoogleAuthConfig(
        mode="google" if configured else "stub",
        configured=configured,
        client_id=settings.google_client_id if configured else None,
        authorization_url=authorization_url,
        detail=(
            "Google OAuth is configured. Send a Google id_token or authorization_code to /api/auth/google/complete."
            if configured
            else "Google OAuth is not configured; local stub login remains available for development."
        ),
    )


@router.post("/google/complete", response_model=AuthSessionResponse)
def google_complete(payload: GoogleCompleteRequest, request: Request) -> AuthSessionResponse:
    settings = _settings(request)
    identity = _google_identity(payload, settings)
    auth = create_session(
        request.app.state.store,
        email=identity.email,
        name=identity.name,
        role=payload.role,
        google_subject=identity.google_id,
        avatar_url=identity.avatar_url,
        auth_store=getattr(request.app.state, "auth_store", None),
        jwt_secret=settings.aimada_jwt_secret,
        jwt_expires_in_seconds=settings.aimada_jwt_expires_in_seconds,
        jwt_issuer=settings.aimada_jwt_issuer,
    )
    restored = restore_latest_history(
        request.app.state.store,
        user_id=str(auth["user"]["user_id"]),
        session_id=str(auth["session"]["session_id"]),
    )
    return AuthSessionResponse(
        user=auth["user"],
        session=auth["session"],
        restored_history=restored,
        access_token=auth.get("access_token"),
        token_type=auth.get("token_type"),
    )


@router.get("/me", response_model=AuthSessionResponse)
def me(
    request: Request,
    x_aimada_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthSessionResponse:
    current = _current_auth(request, x_aimada_session_id, authorization)
    if current is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return AuthSessionResponse(user=current["user"], session=current["session"], restored_history=None)


@router.patch("/role", response_model=AuthSessionResponse)
def select_role(
    payload: RoleUpdateRequest,
    request: Request,
    x_aimada_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthSessionResponse:
    current = _current_auth(request, x_aimada_session_id, authorization)
    if current is None:
        raise HTTPException(status_code=401, detail="not logged in")
    updated = update_role(request.app.state.store, session_id=str(current["session"]["session_id"]), role=payload.role)
    if updated is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return AuthSessionResponse(user=updated["user"], session=updated["session"], restored_history=None)


@router.post("/session/save", response_model=SessionSaveResponse)
def save_current_session(
    payload: SessionSaveRequest,
    request: Request,
    x_aimada_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> SessionSaveResponse:
    current = _current_auth(request, x_aimada_session_id, authorization)
    if current is None:
        raise HTTPException(status_code=401, detail="not logged in")
    snapshot = save_session_history(request.app.state.store, session_id=str(current["session"]["session_id"]), window_hours=payload.window_hours)
    if snapshot is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return SessionSaveResponse(saved=True, snapshot=snapshot)


@router.post("/logout", response_model=SessionSaveResponse)
def logout(
    payload: SessionSaveRequest,
    request: Request,
    x_aimada_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> SessionSaveResponse:
    current = _current_auth(request, x_aimada_session_id, authorization)
    if current is None:
        raise HTTPException(status_code=401, detail="not logged in")
    session_id = str(current["session"]["session_id"])
    snapshot = save_session_history(request.app.state.store, session_id=session_id, window_hours=payload.window_hours)
    closed = close_session(request.app.state.store, session_id=session_id)
    if snapshot is None or closed is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return SessionSaveResponse(saved=True, snapshot=snapshot)


def _google_identity(payload: GoogleCompleteRequest, settings: Any) -> GoogleIdentity:
    if settings.google_client_id:
        id_token = payload.id_token
        code = payload.authorization_code or payload.code
        if code:
            if not settings.google_client_secret:
                raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_SECRET is required for authorization_code login")
            try:
                id_token = exchange_code_for_id_token(
                    code=code,
                    client_id=settings.google_client_id,
                    client_secret=settings.google_client_secret,
                    redirect_uri=payload.redirect_uri,
                )
            except GoogleOAuthError as exc:
                raise HTTPException(status_code=401, detail=f"Google authorization code exchange failed: {exc}") from exc
            except Exception as exc:  # pragma: no cover - network/provider failure path
                raise HTTPException(status_code=401, detail="Google authorization code exchange failed") from exc
        if not id_token:
            raise HTTPException(status_code=400, detail="id_token or authorization_code is required")
        try:
            return verify_google_id_token(id_token, client_id=settings.google_client_id)
        except GoogleTokenVerificationError as exc:
            raise HTTPException(status_code=401, detail=f"Google token verification failed: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Google token verification failed") from exc

    google_id = payload.google_subject or payload.id_token or f"stub:{payload.email}"
    return GoogleIdentity(
        google_id=google_id,
        email=payload.email,
        name=payload.name,
        avatar_url=payload.avatar_url,
    )


def _current_auth(request: Request, session_id: str | None, authorization: str | None) -> dict[str, Any] | None:
    current = find_session(request.app.state.store, session_id)
    if current is not None:
        return current
    settings = _settings(request)
    return find_session_by_jwt(
        request.app.state.store,
        bearer_token_from_authorization(authorization),
        jwt_secret=settings.aimada_jwt_secret,
        jwt_issuer=settings.aimada_jwt_issuer,
    )


def _settings(request: Request) -> Any:
    settings = getattr(request.app.state, "settings", None)
    if settings is not None:
        return settings
    from app.config import get_settings

    return get_settings()
