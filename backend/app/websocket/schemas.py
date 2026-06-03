from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ArenaMessage(BaseModel):
    type: Literal["arena_state"] = "arena_state"
    version: int = Field(default=1, ge=1)
    timestamp: str
    payload: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ArenaMessage":
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )
