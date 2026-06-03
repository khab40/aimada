from fastapi import APIRouter

from app.nebius.client import (
    NebiusClient,
    NebiusIntegrationStatus,
    RedTeamScenarioRequest,
    RedTeamScenarioResponse,
)

router = APIRouter(prefix="/api/nebius", tags=["nebius"])
nebius_client = NebiusClient()


@router.get("/status", response_model=NebiusIntegrationStatus)
def nebius_status() -> NebiusIntegrationStatus:
    return nebius_client.integration_status()


@router.post("/red-team-scenario", response_model=RedTeamScenarioResponse)
def generate_red_team_scenario(request: RedTeamScenarioRequest) -> RedTeamScenarioResponse:
    return nebius_client.generate_red_team_scenario(
        prompt=request.prompt,
        constraints=request.constraints,
    )
