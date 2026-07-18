import asyncio

import httpx
from fastapi import FastAPI

from app.api.routes_kernel import router
from app.contracts.authority import KernelAuthorityRouter
from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.python_reference import PythonReferenceKernel
from tests.test_python_reference_kernel import request


def test_protobuf_kernel_api_runs_through_authority_router_and_exposes_status() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.kernel_authority = KernelAuthorityRouter(PythonReferenceKernel().run)
    simulation_request = request(max_ticks=2)

    response, status = asyncio.run(_run_valid_request(app, simulation_request))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-protobuf"
    assert response.headers["x-kernel-authority"] == "python"
    assert response.headers["x-kernel-decision"] == "python"
    result = exchange_pb2.SimulationResult.FromString(response.content)
    assert result.events
    assert status.json()["mode"] == "python"


def test_protobuf_kernel_api_rejects_invalid_wire_data_and_contract_input() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.kernel_authority = KernelAuthorityRouter(PythonReferenceKernel().run)
    invalid = request(max_ticks=2)
    invalid.contract_version = 2
    malformed, rejected = asyncio.run(_run_invalid_requests(app, invalid))
    assert malformed.status_code == 400
    assert rejected.status_code == 400


async def _run_valid_request(
    app: FastAPI,
    simulation_request: exchange_pb2.SimulationRequest,
) -> tuple[httpx.Response, httpx.Response]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/kernel/run",
            content=simulation_request.SerializeToString(deterministic=True),
            headers={"Content-Type": "application/x-protobuf"},
        )
        return response, await client.get("/api/kernel/status")


async def _run_invalid_requests(
    app: FastAPI,
    invalid: exchange_pb2.SimulationRequest,
) -> tuple[httpx.Response, httpx.Response]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        malformed = await client.post("/api/kernel/run", content=b"\x80")
        rejected = await client.post("/api/kernel/run", content=invalid.SerializeToString())
        return malformed, rejected
