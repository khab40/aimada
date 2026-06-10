from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.persona import (
    SESSION_HEADER,
    ArenaRole,
    close_session,
    create_session,
    find_session,
    restore_latest_history,
    save_session_history,
    update_role,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleAuthConfig(BaseModel):
    mode: str
    configured: bool
    authorization_url: str | None = None
    detail: str


class GoogleCompleteRequest(BaseModel):
    id_token: str | None = None
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


class SessionSaveResponse(BaseModel):
    saved: bool
    snapshot: dict[str, Any] | None = None


@router.get("/google/config", response_model=GoogleAuthConfig)
def google_config() -> GoogleAuthConfig:
    return GoogleAuthConfig(
        mode="stub",
        configured=False,
        authorization_url=None,
        detail="Google OAuth endpoints are not configured yet. Use /api/auth/google/complete as the integration seam.",
    )


@router.post("/google/complete", response_model=AuthSessionResponse)
def google_complete(payload: GoogleCompleteRequest, request: Request) -> AuthSessionResponse:
    auth = create_session(
        request.app.state.store,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        google_subject=payload.google_subject or payload.id_token,
        avatar_url=payload.avatar_url,
    )
    restored = restore_latest_history(
        request.app.state.store,
        user_id=str(auth["user"]["user_id"]),
        session_id=str(auth["session"]["session_id"]),
    )
    return AuthSessionResponse(user=auth["user"], session=auth["session"], restored_history=restored)


@router.get("/me", response_model=AuthSessionResponse)
def me(request: Request, x_nmaa_session_id: str | None = Header(default=None, alias=SESSION_HEADER)) -> AuthSessionResponse:
    current = find_session(request.app.state.store, x_nmaa_session_id)
    if current is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return AuthSessionResponse(user=current["user"], session=current["session"], restored_history=None)


@router.patch("/role", response_model=AuthSessionResponse)
def select_role(
    payload: RoleUpdateRequest,
    request: Request,
    x_nmaa_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
) -> AuthSessionResponse:
    current = update_role(request.app.state.store, session_id=x_nmaa_session_id or "", role=payload.role)
    if current is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return AuthSessionResponse(user=current["user"], session=current["session"], restored_history=None)


@router.post("/session/save", response_model=SessionSaveResponse)
def save_current_session(
    payload: SessionSaveRequest,
    request: Request,
    x_nmaa_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
) -> SessionSaveResponse:
    snapshot = save_session_history(request.app.state.store, session_id=x_nmaa_session_id or "", window_hours=payload.window_hours)
    if snapshot is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return SessionSaveResponse(saved=True, snapshot=snapshot)


@router.post("/logout", response_model=SessionSaveResponse)
def logout(
    payload: SessionSaveRequest,
    request: Request,
    x_nmaa_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
) -> SessionSaveResponse:
    snapshot = save_session_history(request.app.state.store, session_id=x_nmaa_session_id or "", window_hours=payload.window_hours)
    closed = close_session(request.app.state.store, session_id=x_nmaa_session_id or "")
    if snapshot is None or closed is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return SessionSaveResponse(saved=True, snapshot=snapshot)
