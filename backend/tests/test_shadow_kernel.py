from threading import Event

from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.python_reference import PythonReferenceKernel
from app.contracts.shadow import (
    GrpcKernelRunner,
    LiveShadowKernel,
    OfflineShadowKernel,
    ShadowMetrics,
    ShadowOutcome,
)
from tests.test_python_reference_kernel import request


def test_offline_shadow_preserves_python_authority_for_match_mismatch_and_error() -> None:
    reference = PythonReferenceKernel().run
    expected = reference(request(max_ticks=2))

    matching = OfflineShadowKernel(reference, lambda _request: _clone(expected)).run(request(max_ticks=2))
    assert matching.authoritative_result == expected
    assert matching.outcome.status == "match"

    divergent = _clone(expected)
    divergent.metrics[0].quantized_value += 1
    mismatch = OfflineShadowKernel(reference, lambda _request: divergent).run(request(max_ticks=2))
    assert mismatch.authoritative_result == expected
    assert mismatch.outcome.status == "mismatch"
    assert mismatch.outcome.report is not None
    assert mismatch.outcome.report.mismatch_categories == ("metrics",)

    def failed_candidate(_request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        raise TimeoutError("candidate deadline")

    failed = OfflineShadowKernel(reference, failed_candidate).run(request(max_ticks=2))
    assert failed.authoritative_result == expected
    assert failed.candidate_result is None
    assert failed.outcome.status == "error"
    assert failed.outcome.error_type == "TimeoutError"


def test_live_shadow_returns_python_before_candidate_and_records_match() -> None:
    candidate_started = Event()
    release_candidate = Event()
    outcomes: list[ShadowOutcome] = []

    def candidate(candidate_request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        candidate_started.set()
        assert release_candidate.wait(timeout=5)
        return PythonReferenceKernel().run(candidate_request)

    shadow = LiveShadowKernel(PythonReferenceKernel().run, candidate, outcomes.append)
    authoritative = shadow.run(request(max_ticks=2))

    assert authoritative.events
    assert candidate_started.wait(timeout=1)
    assert outcomes == []
    release_candidate.set()
    assert shadow.drain(timeout_seconds=5)
    shadow.close()
    assert [outcome.status for outcome in outcomes] == ["match"]


def test_live_shadow_bounds_pending_work_without_changing_python_result() -> None:
    release_candidate = Event()
    outcomes: list[ShadowOutcome] = []

    def candidate(candidate_request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        assert release_candidate.wait(timeout=5)
        return PythonReferenceKernel().run(candidate_request)

    shadow = LiveShadowKernel(
        PythonReferenceKernel().run,
        candidate,
        outcomes.append,
        max_workers=1,
        max_pending=1,
    )
    first = shadow.run(request(max_ticks=2))
    second_request = request(max_ticks=2)
    second_request.run_id = "PARITY-RUN-002"
    second = shadow.run(second_request)

    assert first.events and second.events
    assert outcomes[0].status == "skipped"
    assert outcomes[0].run_id == "PARITY-RUN-002"
    release_candidate.set()
    assert shadow.drain(timeout_seconds=5)
    shadow.close()
    assert sorted(outcome.status for outcome in outcomes) == ["match", "skipped"]
    metrics = shadow.metrics.snapshot()
    assert metrics["pending"] == 0
    assert metrics["pending_limit"] == 1
    assert metrics["outcomes"]["match"] == 1
    assert metrics["outcomes"]["skipped"] == 1
    assert "lob_kernel_shadow_pending 0" in shadow.metrics.prometheus()


def test_grpc_candidate_runner_calls_generated_service_with_deadline() -> None:
    channel = FakeChannel()
    with GrpcKernelRunner("java-kernel:50051", timeout_seconds=2, channel=channel) as candidate:
        result = candidate(request(max_ticks=2))

    assert result.events
    assert channel.method == "/lob.exchange.v1.SimulationKernel/RunSimulation"
    assert channel.timeout == 2
    assert channel.closed


def test_shadow_settings_and_outcome_validation() -> None:
    try:
        GrpcKernelRunner(" ")
    except ValueError as exception:
        assert "target" in str(exception)
    else:
        raise AssertionError("empty target must fail")
    try:
        LiveShadowKernel(
            PythonReferenceKernel().run,
            PythonReferenceKernel().run,
            lambda _outcome: None,
            max_pending=0,
        )
    except ValueError as exception:
        assert "max_pending" in str(exception)
    else:
        raise AssertionError("zero max_pending must fail")


def test_live_shadow_sink_failure_does_not_change_authoritative_result() -> None:
    def failed_sink(_outcome: ShadowOutcome) -> None:
        raise RuntimeError("sink unavailable")

    shadow = LiveShadowKernel(PythonReferenceKernel().run, PythonReferenceKernel().run, failed_sink)
    authoritative = shadow.run(request(max_ticks=2))
    assert authoritative.events
    assert shadow.drain(timeout_seconds=5)
    shadow.close()


def test_shadow_metrics_use_only_bounded_status_labels() -> None:
    metrics = ShadowMetrics(pending_limit=4)
    metrics.set_pending(2)
    metrics.observe(
        ShadowOutcome(
            run_id="RUN-1",
            mode="live",
            status="error",
            error_type="TimeoutError",
            candidate_duration_seconds=0.25,
        )
    )

    rendered = metrics.prometheus()
    assert 'lob_kernel_shadow_outcomes_total{status="error"} 1' in rendered
    assert 'lob_kernel_shadow_candidate_duration_seconds_sum{status="error"} 0.25' in rendered
    assert "RUN-1" not in rendered


def _clone(result: exchange_pb2.SimulationResult) -> exchange_pb2.SimulationResult:
    return exchange_pb2.SimulationResult.FromString(result.SerializeToString(deterministic=True))


class FakeChannel:
    def __init__(self) -> None:
        self.method = ""
        self.timeout: float | None = None
        self.closed = False

    def unary_unary(self, method: str, **_kwargs: object):
        self.method = method

        def call(
            candidate_request: exchange_pb2.SimulationRequest,
            *,
            timeout: float,
        ) -> exchange_pb2.SimulationResult:
            self.timeout = timeout
            return PythonReferenceKernel().run(candidate_request)

        return call

    def close(self) -> None:
        self.closed = True
