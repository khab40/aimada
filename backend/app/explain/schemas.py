from pydantic import BaseModel


class ExplainResponse(BaseModel):
    summary: str
    source: str = "local-stub"
