import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.parity import KernelRunner, ParityReport, compare_simulation_results
from app.contracts.python_reference import PythonReferenceKernel
from app.contracts.shadow import GrpcKernelRunner, LiveShadowKernel, ShadowOutcome

AuthorityMode = Literal["python", "shadow", "java"]
DecisionSink = Callable[["AuthorityDecision"], None]
LOGGER = logging.getLogger(__name__)


class KernelAuthorityError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthorityDecision:
    run_id: str
    configured_mode: AuthorityMode
    selected_authority: Literal["python", "java"]
    outcome: Literal[
        "python",
        "shadow_python",
        "holdback_python",
        "java",
        "fallback_error",
        "fallback_mismatch",
    ]
    parity_report: ParityReport | None = None
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "configured_mode": self.configured_mode,
            "selected_authority": self.selected_authority,
            "outcome": self.outcome,
        }
        if self.parity_report is not None:
            payload["parity_report"] = self.parity_report.to_dict()
        if self.fallback_reason is not None:
            payload["fallback_reason"] = self.fallback_reason
        return payload


@dataclass(frozen=True)
class AuthorityRun:
    result: exchange_pb2.SimulationResult
    decision: AuthorityDecision


class KernelAuthorityRouter:
    def __init__(
        self,
        reference: KernelRunner,
        *,
        mode: AuthorityMode = "python",
        candidate: KernelRunner | None = None,
        rollout_percentage: int = 0,
        python_replay_percentage: int = 100,
        fallback_to_python: bool = True,
        decision_sink: DecisionSink | None = None,
        shadow_sink: Callable[[ShadowOutcome], None] | None = None,
        shadow_workers: int = 1,
        shadow_max_pending: int = 16,
    ) -> None:
        if mode not in {"python", "shadow", "java"}:
            raise ValueError(f"unsupported kernel authority mode: {mode}")
        if not 0 <= rollout_percentage <= 100:
            raise ValueError("rollout_percentage must be between 0 and 100")
        if not 0 <= python_replay_percentage <= 100:
            raise ValueError("python_replay_percentage must be between 0 and 100")
        if mode != "python" and candidate is None:
            raise ValueError(f"candidate is required for {mode} mode")
        self._reference = reference
        self._candidate = candidate
        self.mode = mode
        self.rollout_percentage = rollout_percentage
        self.python_replay_percentage = python_replay_percentage
        self.fallback_to_python = fallback_to_python
        self._decision_sink = decision_sink
        self._shadow = None
        if mode == "shadow":
            self._shadow = LiveShadowKernel(
                reference,
                candidate,
                shadow_sink or (lambda _outcome: None),
                max_workers=shadow_workers,
                max_pending=shadow_max_pending,
            )

    def run(self, request: exchange_pb2.SimulationRequest) -> AuthorityRun:
        request_bytes = request.SerializeToString(deterministic=True)
        if self.mode == "python":
            return self._publish(
                self._reference(_request(request_bytes)),
                AuthorityDecision(request.run_id, "python", "python", "python"),
            )
        if self.mode == "shadow":
            result = self._shadow.run(_request(request_bytes))
            return self._publish(
                result,
                AuthorityDecision(request.run_id, "shadow", "python", "shadow_python"),
            )
        if not _selected(request.run_id, self.rollout_percentage, "java-authority"):
            return self._publish(
                self._reference(_request(request_bytes)),
                AuthorityDecision(request.run_id, "java", "python", "holdback_python"),
            )

        try:
            candidate_result = self._candidate(_request(request_bytes))
        except Exception as exception:
            if not self.fallback_to_python:
                raise KernelAuthorityError(f"Java kernel failed: {type(exception).__name__}") from exception
            return self._publish(
                self._reference(_request(request_bytes)),
                AuthorityDecision(
                    request.run_id,
                    "java",
                    "python",
                    "fallback_error",
                    fallback_reason=type(exception).__name__,
                ),
            )

        if _selected(request.run_id, self.python_replay_percentage, "python-replay"):
            reference_result = self._reference(_request(request_bytes))
            report = compare_simulation_results(reference_result, candidate_result)
            if not report.matches:
                if not self.fallback_to_python:
                    raise KernelAuthorityError(
                        f"Java kernel parity mismatch: {','.join(report.mismatch_categories)}"
                    )
                return self._publish(
                    reference_result,
                    AuthorityDecision(
                        request.run_id,
                        "java",
                        "python",
                        "fallback_mismatch",
                        parity_report=report,
                        fallback_reason=",".join(report.mismatch_categories),
                    ),
                )
            decision = AuthorityDecision(
                request.run_id,
                "java",
                "java",
                "java",
                parity_report=report,
            )
        else:
            decision = AuthorityDecision(request.run_id, "java", "java", "java")
        return self._publish(candidate_result, decision)

    def status(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": self.mode,
            "rollout_percentage": self.rollout_percentage,
            "python_replay_percentage": self.python_replay_percentage,
            "fallback_to_python": self.fallback_to_python,
        }
        if self._shadow is not None:
            payload["shadow_metrics"] = self._shadow.metrics.snapshot()
        return payload

    def prometheus(self) -> str:
        return "" if self._shadow is None else self._shadow.metrics.prometheus()

    def close(self) -> None:
        if self._shadow is not None:
            self._shadow.close(wait_for_pending=True)
        close = getattr(self._candidate, "close", None)
        if callable(close):
            close()

    def _publish(self, result: exchange_pb2.SimulationResult, decision: AuthorityDecision) -> AuthorityRun:
        if self._decision_sink is not None:
            try:
                self._decision_sink(decision)
            except Exception:
                LOGGER.exception("kernel authority decision sink failed for run %s", decision.run_id)
        return AuthorityRun(result=result, decision=decision)


def create_authority_router(
    settings: Any,
    *,
    decision_sink: DecisionSink | None = None,
    shadow_sink: Callable[[ShadowOutcome], None] | None = None,
) -> KernelAuthorityRouter:
    mode: AuthorityMode = settings.kernel_authority_mode
    candidate = None
    if mode != "python":
        candidate = GrpcKernelRunner(
            settings.java_kernel_grpc_target,
            timeout_seconds=settings.java_kernel_grpc_timeout_seconds,
        )
    return KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode=mode,
        candidate=candidate,
        rollout_percentage=settings.java_kernel_rollout_percentage,
        python_replay_percentage=settings.java_kernel_python_replay_percentage,
        fallback_to_python=settings.java_kernel_fallback_to_python,
        decision_sink=decision_sink,
        shadow_sink=shadow_sink,
        shadow_workers=settings.java_kernel_shadow_workers,
        shadow_max_pending=settings.java_kernel_shadow_max_pending,
    )


def _selected(run_id: str, percentage: int, salt: str) -> bool:
    if percentage <= 0:
        return False
    if percentage >= 100:
        return True
    digest = hashlib.sha256(f"{salt}:{run_id}".encode()).digest()
    bucket = int.from_bytes(digest[:4], "big") % 10_000
    return bucket < percentage * 100


def _request(request_bytes: bytes) -> exchange_pb2.SimulationRequest:
    return exchange_pb2.SimulationRequest.FromString(request_bytes)
