from unittest.mock import Mock

import grpc
import pytest

from app.contracts.generated.lob.exchange.v1 import exchange_pb2_grpc
from app.contracts.grpc_reference import PythonReferenceKernelServicer, create_reference_grpc_server
from tests.test_python_reference_kernel import request


def test_python_grpc_servicer_delegates_to_reference_kernel() -> None:
    context = Mock(spec=grpc.ServicerContext)

    result = PythonReferenceKernelServicer().RunSimulation(request(max_ticks=2), context)

    assert result.run_id == "PARITY-RUN-001"
    assert result.events
    context.abort.assert_not_called()


def test_python_grpc_servicer_maps_contract_errors_to_invalid_argument() -> None:
    context = Mock(spec=grpc.ServicerContext)
    context.abort.side_effect = RuntimeError("aborted")
    invalid = request()
    invalid.contract_version = 2

    with pytest.raises(RuntimeError, match="aborted"):
        PythonReferenceKernelServicer().RunSimulation(invalid, context)

    context.abort.assert_called_once()
    assert context.abort.call_args.args[0] == grpc.StatusCode.INVALID_ARGUMENT


def test_reference_server_registers_generated_service_and_validates_workers() -> None:
    server = create_reference_grpc_server()
    assert isinstance(PythonReferenceKernelServicer(), exchange_pb2_grpc.SimulationKernelServicer)
    server.stop(grace=None)
    with pytest.raises(ValueError, match="positive"):
        create_reference_grpc_server(max_workers=0)
