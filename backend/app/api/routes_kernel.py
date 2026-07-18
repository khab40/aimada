import asyncio

from fastapi import APIRouter, HTTPException, Request, Response
from google.protobuf.message import DecodeError

from app.contracts.authority import KernelAuthorityError
from app.contracts.generated.lob.exchange.v1 import exchange_pb2

router = APIRouter(prefix="/api/kernel", tags=["kernel"])
MAX_REQUEST_BYTES = 8 * 1024 * 1024


@router.get("/status")
def kernel_status(request: Request) -> dict[str, object]:
    return request.app.state.kernel_authority.status()


@router.post("/run")
async def run_kernel(request: Request) -> Response:
    body = await request.body()
    if len(body) > MAX_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail="Protobuf kernel request exceeds 8 MiB")
    try:
        simulation_request = exchange_pb2.SimulationRequest.FromString(body)
    except DecodeError as exception:
        raise HTTPException(status_code=400, detail="invalid SimulationRequest Protobuf") from exception
    try:
        run = await asyncio.to_thread(request.app.state.kernel_authority.run, simulation_request)
    except KernelAuthorityError as exception:
        raise HTTPException(status_code=503, detail=str(exception)) from exception
    except ValueError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception
    return Response(
        content=run.result.SerializeToString(deterministic=True),
        media_type="application/x-protobuf",
        headers={
            "X-Kernel-Authority": run.decision.selected_authority,
            "X-Kernel-Decision": run.decision.outcome,
        },
    )
