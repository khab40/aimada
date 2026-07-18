import logging
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Literal

import grpc

from app.contracts.generated.lob.exchange.v1 import exchange_pb2, exchange_pb2_grpc
from app.contracts.parity import KernelRunner, ParityReport, compare_simulation_results

ShadowStatus = Literal["match", "mismatch", "error", "skipped"]
ShadowSink = Callable[["ShadowOutcome"], None]
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShadowOutcome:
    run_id: str
    mode: Literal["offline", "live"]
    status: ShadowStatus
    report: ParityReport | None = None
    error_type: str | None = None
    error_detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
        }
        if self.report is not None:
            payload["report"] = self.report.to_dict()
        if self.error_type is not None:
            payload["error_type"] = self.error_type
        if self.error_detail is not None:
            payload["error_detail"] = self.error_detail
        return payload


@dataclass(frozen=True)
class OfflineShadowRun:
    authoritative_result: exchange_pb2.SimulationResult
    candidate_result: exchange_pb2.SimulationResult | None
    outcome: ShadowOutcome


class GrpcKernelRunner:
    def __init__(
        self,
        target: str,
        *,
        timeout_seconds: float = 5.0,
        channel: grpc.Channel | None = None,
    ) -> None:
        if not target.strip():
            raise ValueError("gRPC target must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("gRPC timeout must be positive")
        self._timeout_seconds = timeout_seconds
        self._channel = channel or grpc.insecure_channel(target)
        self._stub = exchange_pb2_grpc.SimulationKernelStub(self._channel)

    def __call__(self, request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        return self._stub.RunSimulation(request, timeout=self._timeout_seconds)

    def close(self) -> None:
        self._channel.close()

    def __enter__(self) -> "GrpcKernelRunner":
        return self

    def __exit__(self, _exc_type: object, _exc_value: object, _traceback: object) -> None:
        self.close()


class OfflineShadowKernel:
    """Run both kernels synchronously while preserving the Python result as authority."""

    def __init__(self, reference: KernelRunner, candidate: KernelRunner) -> None:
        self._reference = reference
        self._candidate = candidate

    def run(self, request: exchange_pb2.SimulationRequest) -> OfflineShadowRun:
        request_bytes = request.SerializeToString(deterministic=True)
        authoritative = self._reference(exchange_pb2.SimulationRequest.FromString(request_bytes))
        try:
            candidate = self._candidate(exchange_pb2.SimulationRequest.FromString(request_bytes))
        except Exception as exception:
            return OfflineShadowRun(
                authoritative_result=authoritative,
                candidate_result=None,
                outcome=_error_outcome(request.run_id, "offline", exception),
            )
        report = compare_simulation_results(authoritative, candidate)
        return OfflineShadowRun(
            authoritative_result=authoritative,
            candidate_result=candidate,
            outcome=ShadowOutcome(
                run_id=request.run_id,
                mode="offline",
                status="match" if report.matches else "mismatch",
                report=report,
            ),
        )


class LiveShadowKernel:
    """Return Python authority immediately and compare the Java candidate in bounded background work."""

    def __init__(
        self,
        reference: KernelRunner,
        candidate: KernelRunner,
        sink: ShadowSink,
        *,
        max_workers: int = 1,
        max_pending: int = 16,
    ) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be positive")
        if max_pending <= 0:
            raise ValueError("max_pending must be positive")
        self._reference = reference
        self._candidate = candidate
        self._sink = sink
        self._max_pending = max_pending
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="kernel-shadow")
        self._pending: set[Future[ShadowOutcome]] = set()
        self._lock = Lock()
        self._closed = False

    def run(self, request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        request_bytes = request.SerializeToString(deterministic=True)
        authoritative = self._reference(exchange_pb2.SimulationRequest.FromString(request_bytes))
        authoritative_bytes = authoritative.SerializeToString(deterministic=True)
        skipped: ShadowOutcome | None = None
        future: Future[ShadowOutcome] | None = None
        with self._lock:
            if self._closed:
                raise RuntimeError("live shadow kernel is closed")
            if len(self._pending) >= self._max_pending:
                skipped = ShadowOutcome(
                    run_id=request.run_id,
                    mode="live",
                    status="skipped",
                    error_type="ShadowCapacityExceeded",
                    error_detail=f"maximum pending shadow runs reached: {self._max_pending}",
                )
            else:
                future = self._executor.submit(self._compare, request_bytes, authoritative_bytes)
                self._pending.add(future)
        if skipped is not None:
            self._emit(skipped)
        if future is not None:
            future.add_done_callback(self._complete)
        return authoritative

    def drain(self, timeout_seconds: float | None = None) -> bool:
        with self._lock:
            pending = tuple(self._pending)
        if not pending:
            return True
        _, unfinished = wait(pending, timeout=timeout_seconds)
        return not unfinished

    def close(self, *, wait_for_pending: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait_for_pending, cancel_futures=not wait_for_pending)

    def _compare(self, request_bytes: bytes, authoritative_bytes: bytes) -> ShadowOutcome:
        request = exchange_pb2.SimulationRequest.FromString(request_bytes)
        try:
            candidate = self._candidate(request)
        except Exception as exception:
            return _error_outcome(request.run_id, "live", exception)
        authoritative = exchange_pb2.SimulationResult.FromString(authoritative_bytes)
        report = compare_simulation_results(authoritative, candidate)
        return ShadowOutcome(
            run_id=request.run_id,
            mode="live",
            status="match" if report.matches else "mismatch",
            report=report,
        )

    def _complete(self, future: Future[ShadowOutcome]) -> None:
        try:
            outcome = future.result()
        except Exception as exception:
            outcome = _error_outcome("unknown", "live", exception)
        try:
            self._emit(outcome)
        finally:
            with self._lock:
                self._pending.discard(future)

    def _emit(self, outcome: ShadowOutcome) -> None:
        try:
            self._sink(outcome)
        except Exception:
            LOGGER.exception("kernel shadow outcome sink failed for run %s", outcome.run_id)


def _error_outcome(
    run_id: str,
    mode: Literal["offline", "live"],
    exception: Exception,
) -> ShadowOutcome:
    return ShadowOutcome(
        run_id=run_id,
        mode=mode,
        status="error",
        error_type=type(exception).__name__,
        error_detail=str(exception)[:500],
    )
