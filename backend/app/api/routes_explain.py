from fastapi import APIRouter
from pydantic import BaseModel

from app.explain.client import ExplainClient

router = APIRouter(prefix="/explain", tags=["explain"])
client = ExplainClient()


class ExplainRequest(BaseModel):
    payload: dict[str, object]


@router.post("/event")
def explain_event(request: ExplainRequest) -> dict[str, object]:
    return client.explain_event(request.payload)


@router.post("/simulation")
def explain_simulation(request: ExplainRequest) -> dict[str, object]:
    return client.explain_simulation(request.payload)


@router.post("/incident-report")
def generate_incident_report(request: ExplainRequest) -> dict[str, object]:
    return client.generate_incident_report(request.payload)
