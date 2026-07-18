import json
from pathlib import Path

from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.parity import DifferentialParityHarness, compare_simulation_results
from app.contracts.python_reference import PythonReferenceKernel

ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = ROOT / "contracts" / "golden" / "parity-v1"


def test_harness_reports_exact_parity_for_every_golden_case_and_clones_requests() -> None:
    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    observed_request_bytes: list[bytes] = []

    def candidate(request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        observed_request_bytes.append(request.SerializeToString(deterministic=True))
        case = next(
            item
            for item in manifest["cases"]
            if item["scenario_name"] == request.scenario.scenario_name and item["seed"] == request.scenario.seed
        )
        result = _result(case["expected_result_file"])
        result.run_id = request.run_id
        return result

    def reference(request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        original_bytes = request.SerializeToString(deterministic=True)
        request.run_id = "MUTATED-BY-REFERENCE"
        observed_request_bytes.append(original_bytes)
        return PythonReferenceKernel().run(exchange_pb2.SimulationRequest.FromString(original_bytes))

    harness = DifferentialParityHarness(reference, candidate)
    for case in manifest["cases"]:
        request = _request(case["request_file"])
        request.run_id = case["case_id"].upper()
        expected_bytes = request.SerializeToString(deterministic=True)

        run = harness.run(request)

        assert run.report.matches
        assert run.report.mismatch_categories == ()
        assert run.report.first_event_divergence_sequence is None
        assert run.report.to_dict()["matches"] is True
        assert request.SerializeToString(deterministic=True) == expected_bytes
        assert observed_request_bytes[-2:] == [expected_bytes, expected_bytes]


def test_report_pinpoints_event_execution_and_hash_divergence() -> None:
    reference = _result("cases/normal-market-seed-42/expected-result.pb")
    candidate = _clone(reference)
    event_index = next(index for index, event in enumerate(candidate.events) if event.HasField("execute"))
    candidate.events[event_index].execute.quantity_lots += 1
    candidate.event_stream_hash = b"candidate-hash"

    report = compare_simulation_results(reference, candidate)

    assert not report.matches
    assert report.first_event_divergence_sequence == reference.events[event_index].metadata.sequence
    assert report.mismatch_categories == ("events", "event_hash", "executions")
    assert report.reference_execution_count == report.candidate_execution_count == 1


def test_report_separates_snapshot_final_book_metric_and_termination_divergence() -> None:
    reference = _result("cases/normal-market-seed-42/expected-result.pb")
    candidate = _clone(reference)
    snapshot_index = next(index for index, event in enumerate(candidate.events) if event.HasField("snapshot"))
    candidate.events[snapshot_index].snapshot.book.bids[0].quantity_lots += 1
    candidate.final_book.asks[0].quantity_lots += 1
    candidate.final_book_hash = b"candidate-book-hash"
    candidate.metrics[0].quantized_value += 1
    candidate.termination_reason = exchange_pb2.TERMINATION_REASON_FAILED
    candidate.termination_detail = "candidate failed"

    report = compare_simulation_results(reference, candidate)

    assert report.mismatch_categories == (
        "events",
        "snapshots",
        "final_book",
        "final_book_hash",
        "metrics",
        "termination",
    )
    assert report.reference_snapshot_count == report.candidate_snapshot_count
    assert report.to_dict()["mismatches"]


def test_report_detects_contract_identity_and_missing_tail_event() -> None:
    reference = _result("cases/empty-book-seed-7/expected-result.pb")
    candidate = _clone(reference)
    candidate.contract_version = 2
    candidate.run_id = "OTHER-RUN"
    del candidate.events[-1]

    report = compare_simulation_results(reference, candidate)

    assert report.mismatch_categories == ("contract", "events", "snapshots")
    assert report.reference_event_count == 3
    assert report.candidate_event_count == 2
    assert report.first_event_divergence_sequence == 3


def _request(relative_path: str) -> exchange_pb2.SimulationRequest:
    return exchange_pb2.SimulationRequest.FromString((CORPUS_ROOT / relative_path).read_bytes())


def _result(relative_path: str) -> exchange_pb2.SimulationResult:
    return exchange_pb2.SimulationResult.FromString((CORPUS_ROOT / relative_path).read_bytes())


def _clone(result: exchange_pb2.SimulationResult) -> exchange_pb2.SimulationResult:
    return exchange_pb2.SimulationResult.FromString(result.SerializeToString(deterministic=True))
