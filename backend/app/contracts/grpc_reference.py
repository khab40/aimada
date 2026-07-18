from concurrent import futures

import grpc

from app.contracts.generated.lob.exchange.v1 import exchange_pb2, exchange_pb2_grpc
from app.contracts.python_reference import PythonReferenceKernel, ReferenceKernelError


class PythonReferenceKernelServicer(exchange_pb2_grpc.SimulationKernelServicer):
    def __init__(self, kernel: PythonReferenceKernel | None = None) -> None:
        self._kernel = kernel or PythonReferenceKernel()

    def RunSimulation(
        self,
        request: exchange_pb2.SimulationRequest,
        context: grpc.ServicerContext,
    ) -> exchange_pb2.SimulationResult:
        try:
            return self._kernel.run(request)
        except ReferenceKernelError as exc:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            raise AssertionError("grpc context.abort must not return") from exc


def create_reference_grpc_server(*, max_workers: int = 1) -> grpc.Server:
    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    exchange_pb2_grpc.add_SimulationKernelServicer_to_server(PythonReferenceKernelServicer(), server)
    return server
