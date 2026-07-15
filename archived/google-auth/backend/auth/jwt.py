import base64
import hashlib
import hmac
import json
import time
from typing import Any


def create_jwt(payload: dict[str, Any], *, secret: str, expires_in_seconds: int, issuer: str) -> str:
    now = int(time.time())
    claims = {
        **payload,
        "iss": issuer,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64_json(header)}.{_b64_json(claims)}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def verify_jwt(token: str, *, secret: str, issuer: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid JWT format")
    signing_input = f"{parts[0]}.{parts[1]}"
    expected = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    actual = _b64_decode(parts[2])
    if not hmac.compare_digest(expected, actual):
        raise ValueError("invalid JWT signature")
    claims = json.loads(_b64_decode(parts[1]).decode("utf-8"))
    if claims.get("iss") != issuer:
        raise ValueError("invalid JWT issuer")
    expires_at = claims.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(time.time()):
        raise ValueError("expired JWT")
    return claims


def _b64_json(payload: dict[str, Any]) -> str:
    return _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))
