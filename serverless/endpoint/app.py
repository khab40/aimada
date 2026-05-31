from fastapi import FastAPI
from pydantic import BaseModel

from prompts import EVENT_PROMPT, INCIDENT_PROMPT, SIMULATION_PROMPT

app = FastAPI(title="Nebius Market Abuse Arena Explain Endpoint")


class ExplainPayload(BaseModel):
    payload: dict[str, object]


@app.post("/explain-event")
def explain_event(request: ExplainPayload) -> dict[str, object]:
    return {"prompt": EVENT_PROMPT, "summary": "Event explanation scaffold.", "payload": request.payload}


@app.post("/explain-simulation")
def explain_simulation(request: ExplainPayload) -> dict[str, object]:
    return {"prompt": SIMULATION_PROMPT, "summary": "Simulation explanation scaffold.", "payload": request.payload}


@app.post("/generate-incident-report")
def generate_incident_report(request: ExplainPayload) -> dict[str, object]:
    return {"prompt": INCIDENT_PROMPT, "summary": "Incident report scaffold.", "payload": request.payload}
