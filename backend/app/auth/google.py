import json
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class GoogleIdentity:
    google_id: str
    email: str
    name: str
    avatar_url: str | None


class GoogleOAuthError(ValueError):
    """Provider-side OAuth failures that are safe to expose as login errors."""


class GoogleTokenVerificationError(ValueError):
    """Google ID token verification failures that are safe to expose as login errors."""


def verify_google_id_token(id_token: str, *, client_id: str) -> GoogleIdentity:
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError as exc:  # pragma: no cover - exercised only in misconfigured deployments
        raise RuntimeError("google-auth is required for Google token verification") from exc

    try:
        payload = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            client_id,
            clock_skew_in_seconds=60,
        )
        return identity_from_google_payload(payload)
    except Exception as exc:
        raise GoogleTokenVerificationError(str(exc) or exc.__class__.__name__) from exc


def exchange_code_for_id_token(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str | None = None,
    token_endpoint: str = "https://oauth2.googleapis.com/token",
) -> str:
    form = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
    }
    if redirect_uri:
        form["redirect_uri"] = redirect_uri
    body = parse.urlencode(form).encode("utf-8")
    req = request.Request(
        token_endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise GoogleOAuthError(_google_error_detail(exc)) from exc
    except URLError as exc:
        raise GoogleOAuthError(f"Google token endpoint was unreachable: {exc.reason}") from exc
    id_token = payload.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise ValueError("Google token endpoint response did not include id_token")
    return id_token


def _google_error_detail(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        return f"Google token endpoint rejected the authorization code with HTTP {exc.code}"
    detail = payload.get("error_description") or payload.get("error")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return f"Google token endpoint rejected the authorization code with HTTP {exc.code}"


def identity_from_google_payload(payload: dict[str, Any]) -> GoogleIdentity:
    google_id = str(payload.get("sub") or "").strip()
    email = str(payload.get("email") or "").strip()
    if not google_id:
        raise ValueError("Google identity payload is missing sub")
    if not email:
        raise ValueError("Google identity payload is missing email")
    email_verified = payload.get("email_verified", True)
    if email_verified is False:
        raise ValueError("Google email is not verified")
    return GoogleIdentity(
        google_id=google_id,
        email=email,
        name=str(payload.get("name") or email).strip(),
        avatar_url=payload.get("picture") if isinstance(payload.get("picture"), str) else None,
    )
