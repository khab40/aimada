from pydantic import BaseModel


class ArenaMessage(BaseModel):
    type: str
    payload: dict[str, object]
