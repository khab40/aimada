from threading import Event

import pytest

from app.config import Settings
from app.contracts.authority import KernelAuthorityError, KernelAuthorityRouter
from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.python_reference import PythonReferenceKernel
from tests.test_python_reference_kernel import request


def test_default_settings_select_full_java_with_sampled_python_replay_and_fallback() -> None:
    settings = Settings(_env_file=None)
    assert settings.kernel_authority_mode == "java"
    assert settings.java_kernel_rollout_percentage == 100
    assert settings.java_kernel_python_replay_percentage == 10
    assert settings.java_kernel_fallback_to_python is True


def test_java_rollout_holdback_never_calls_candidate() -> None:
    candidate_called = False

    def candidate(_request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        nonlocal candidate_called
        candidate_called = True
        raise AssertionError("candidate must not run")

    router = KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode="java",
        candidate=candidate,
        rollout_percentage=0,
    )

    run = router.run(request(max_ticks=2))

    assert not candidate_called
    assert run.decision.outcome == "holdback_python"
    assert run.decision.selected_authority == "python"


def test_java_authority_with_sampled_python_replay_requires_parity() -> None:
    router = KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode="java",
        candidate=PythonReferenceKernel().run,
        rollout_percentage=100,
        python_replay_percentage=100,
    )

    run = router.run(request(max_ticks=2))

    assert run.decision.outcome == "java"
    assert run.decision.selected_authority == "java"
    assert run.decision.parity_report is not None
    assert run.decision.parity_report.matches


def test_java_mismatch_and_error_fall_back_to_python() -> None:
    authoritative = PythonReferenceKernel().run(request(max_ticks=2))
    divergent = _clone(authoritative)
    divergent.metrics[0].quantized_value += 1
    mismatch_router = KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode="java",
        candidate=lambda _request: divergent,
        rollout_percentage=100,
        python_replay_percentage=100,
    )
    mismatch = mismatch_router.run(request(max_ticks=2))
    assert mismatch.result == authoritative
    assert mismatch.decision.outcome == "fallback_mismatch"
    assert mismatch.decision.parity_report is not None

    def failed(_request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        raise TimeoutError("deadline")

    error_router = KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode="java",
        candidate=failed,
        rollout_percentage=100,
    )
    fallback = error_router.run(request(max_ticks=2))
    assert fallback.result == authoritative
    assert fallback.decision.outcome == "fallback_error"
    assert fallback.decision.fallback_reason == "TimeoutError"


def test_java_failure_or_known_mismatch_can_be_configured_to_fail_closed() -> None:
    def failed(_request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        raise TimeoutError("deadline")

    error_router = KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode="java",
        candidate=failed,
        rollout_percentage=100,
        fallback_to_python=False,
    )
    with pytest.raises(KernelAuthorityError, match="TimeoutError"):
        error_router.run(request(max_ticks=2))

    divergent = PythonReferenceKernel().run(request(max_ticks=2))
    divergent.final_book_hash = b"different"
    mismatch_router = KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode="java",
        candidate=lambda _request: divergent,
        rollout_percentage=100,
        python_replay_percentage=100,
        fallback_to_python=False,
    )
    with pytest.raises(KernelAuthorityError, match="final_book_hash"):
        mismatch_router.run(request(max_ticks=2))


def test_shadow_router_returns_python_and_exports_queue_metrics() -> None:
    release = Event()

    def candidate(candidate_request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        assert release.wait(timeout=5)
        return PythonReferenceKernel().run(candidate_request)

    router = KernelAuthorityRouter(
        PythonReferenceKernel().run,
        mode="shadow",
        candidate=candidate,
        shadow_max_pending=2,
    )
    run = router.run(request(max_ticks=2))
    assert run.decision.outcome == "shadow_python"
    assert run.result.events
    assert router.status()["shadow_metrics"]["pending"] == 1
    assert "lob_kernel_shadow_pending 1" in router.prometheus()
    release.set()
    router.close()


def test_decision_sink_failure_and_rollout_sampling_are_deterministic() -> None:
    def failed_sink(_decision: object) -> None:
        raise RuntimeError("store unavailable")

    outcomes = []
    for _ in range(2):
        router = KernelAuthorityRouter(
            PythonReferenceKernel().run,
            mode="java",
            candidate=PythonReferenceKernel().run,
            rollout_percentage=50,
            python_replay_percentage=0,
            decision_sink=failed_sink,
        )
        outcomes.append(router.run(request(max_ticks=2)).decision.outcome)
    assert outcomes[0] == outcomes[1]


def _clone(result: exchange_pb2.SimulationResult) -> exchange_pb2.SimulationResult:
    return exchange_pb2.SimulationResult.FromString(result.SerializeToString(deterministic=True))
