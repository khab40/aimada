from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.contracts.generated.lob.exchange.v1 import exchange_pb2

KernelRunner = Callable[[exchange_pb2.SimulationRequest], exchange_pb2.SimulationResult]


@dataclass(frozen=True)
class ParityMismatch:
    category: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"category": self.category, "detail": self.detail}


@dataclass(frozen=True)
class ParityReport:
    run_id: str
    matches: bool
    reference_event_count: int
    candidate_event_count: int
    reference_execution_count: int
    candidate_execution_count: int
    reference_snapshot_count: int
    candidate_snapshot_count: int
    first_event_divergence_sequence: int | None
    mismatches: tuple[ParityMismatch, ...]

    @property
    def mismatch_categories(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(mismatch.category for mismatch in self.mismatches))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "matches": self.matches,
            "reference_event_count": self.reference_event_count,
            "candidate_event_count": self.candidate_event_count,
            "reference_execution_count": self.reference_execution_count,
            "candidate_execution_count": self.candidate_execution_count,
            "reference_snapshot_count": self.reference_snapshot_count,
            "candidate_snapshot_count": self.candidate_snapshot_count,
            "first_event_divergence_sequence": self.first_event_divergence_sequence,
            "mismatch_categories": list(self.mismatch_categories),
            "mismatches": [mismatch.to_dict() for mismatch in self.mismatches],
        }


@dataclass(frozen=True)
class DifferentialRun:
    reference_result: exchange_pb2.SimulationResult
    candidate_result: exchange_pb2.SimulationResult
    report: ParityReport


class DifferentialParityHarness:
    """Execute identical immutable request bytes against two kernel runners."""

    def __init__(self, reference: KernelRunner, candidate: KernelRunner) -> None:
        self._reference = reference
        self._candidate = candidate

    def run(self, request: exchange_pb2.SimulationRequest) -> DifferentialRun:
        request_bytes = request.SerializeToString(deterministic=True)
        reference_result = self._reference(exchange_pb2.SimulationRequest.FromString(request_bytes))
        candidate_result = self._candidate(exchange_pb2.SimulationRequest.FromString(request_bytes))
        return DifferentialRun(
            reference_result=reference_result,
            candidate_result=candidate_result,
            report=compare_simulation_results(reference_result, candidate_result),
        )


def compare_simulation_results(
    reference: exchange_pb2.SimulationResult,
    candidate: exchange_pb2.SimulationResult,
) -> ParityReport:
    mismatches: list[ParityMismatch] = []

    if reference.contract_version != candidate.contract_version:
        mismatches.append(
            ParityMismatch(
                "contract",
                f"contract_version differs: {reference.contract_version} != {candidate.contract_version}",
            )
        )
    if reference.run_id != candidate.run_id:
        mismatches.append(ParityMismatch("contract", f"run_id differs: {reference.run_id!r} != {candidate.run_id!r}"))

    first_event_divergence = _first_message_divergence(reference.events, candidate.events)
    if len(reference.events) != len(candidate.events):
        mismatches.append(
            ParityMismatch("events", f"event count differs: {len(reference.events)} != {len(candidate.events)}")
        )
    if first_event_divergence is not None:
        mismatches.append(
            ParityMismatch("events", _event_divergence_detail(reference.events, candidate.events, first_event_divergence))
        )

    if reference.event_stream_hash != candidate.event_stream_hash:
        mismatches.append(
            ParityMismatch(
                "event_hash",
                f"event stream hash differs: {reference.event_stream_hash.hex()} != {candidate.event_stream_hash.hex()}",
            )
        )

    reference_executions = tuple(event.execute for event in reference.events if event.WhichOneof("payload") == "execute")
    candidate_executions = tuple(event.execute for event in candidate.events if event.WhichOneof("payload") == "execute")
    execution_divergence = _first_message_divergence(reference_executions, candidate_executions)
    if execution_divergence is not None:
        mismatches.append(
            ParityMismatch(
                "executions",
                _collection_divergence_detail(
                    "execution", reference_executions, candidate_executions, execution_divergence
                ),
            )
        )

    reference_snapshots = tuple(event.snapshot for event in reference.events if event.WhichOneof("payload") == "snapshot")
    candidate_snapshots = tuple(event.snapshot for event in candidate.events if event.WhichOneof("payload") == "snapshot")
    snapshot_divergence = _first_message_divergence(reference_snapshots, candidate_snapshots)
    if snapshot_divergence is not None:
        mismatches.append(
            ParityMismatch(
                "snapshots",
                _collection_divergence_detail("snapshot", reference_snapshots, candidate_snapshots, snapshot_divergence),
            )
        )

    if reference.final_book != candidate.final_book:
        mismatches.append(ParityMismatch("final_book", "final L2 book differs"))
    if reference.final_book_hash != candidate.final_book_hash:
        mismatches.append(
            ParityMismatch(
                "final_book_hash",
                f"final book hash differs: {reference.final_book_hash.hex()} != {candidate.final_book_hash.hex()}",
            )
        )

    metric_divergence = _first_message_divergence(reference.metrics, candidate.metrics)
    if metric_divergence is not None:
        mismatches.append(
            ParityMismatch(
                "metrics",
                _metric_divergence_detail(reference.metrics, candidate.metrics, metric_divergence),
            )
        )

    if (
        reference.termination_reason != candidate.termination_reason
        or reference.HasField("termination_detail") != candidate.HasField("termination_detail")
        or reference.termination_detail != candidate.termination_detail
    ):
        mismatches.append(ParityMismatch("termination", "termination reason or detail differs"))

    reference_execution_count = len(reference_executions)
    candidate_execution_count = len(candidate_executions)
    reference_snapshot_count = len(reference_snapshots)
    candidate_snapshot_count = len(candidate_snapshots)
    first_sequence = None
    if first_event_divergence is not None:
        first_sequence = first_event_divergence + 1
        if first_event_divergence < len(reference.events):
            first_sequence = reference.events[first_event_divergence].metadata.sequence
        elif first_event_divergence < len(candidate.events):
            first_sequence = candidate.events[first_event_divergence].metadata.sequence

    return ParityReport(
        run_id=reference.run_id,
        matches=not mismatches,
        reference_event_count=len(reference.events),
        candidate_event_count=len(candidate.events),
        reference_execution_count=reference_execution_count,
        candidate_execution_count=candidate_execution_count,
        reference_snapshot_count=reference_snapshot_count,
        candidate_snapshot_count=candidate_snapshot_count,
        first_event_divergence_sequence=first_sequence,
        mismatches=tuple(mismatches),
    )


def _first_message_divergence(reference: Any, candidate: Any) -> int | None:
    for index, (reference_item, candidate_item) in enumerate(zip(reference, candidate, strict=False)):
        if reference_item != candidate_item:
            return index
    if len(reference) != len(candidate):
        return min(len(reference), len(candidate))
    return None


def _event_divergence_detail(reference: Any, candidate: Any, index: int) -> str:
    if index >= len(reference):
        return f"candidate has an extra event at index {index}"
    if index >= len(candidate):
        return f"candidate is missing the reference event at index {index}"
    reference_event = reference[index]
    candidate_event = candidate[index]
    return (
        f"event differs at index {index}: reference sequence={reference_event.metadata.sequence} "
        f"type={reference_event.WhichOneof('payload')}, candidate sequence={candidate_event.metadata.sequence} "
        f"type={candidate_event.WhichOneof('payload')}"
    )


def _collection_divergence_detail(kind: str, reference: Any, candidate: Any, index: int) -> str:
    if index >= len(reference):
        return f"candidate has an extra {kind} at index {index}"
    if index >= len(candidate):
        return f"candidate is missing the reference {kind} at index {index}"
    return f"{kind} differs at index {index}"


def _metric_divergence_detail(reference: Any, candidate: Any, index: int) -> str:
    if index >= len(reference):
        return f"candidate has an extra metric at index {index}: {candidate[index].name}"
    if index >= len(candidate):
        return f"candidate is missing the reference metric at index {index}: {reference[index].name}"
    return (
        f"metric differs at index {index}: reference {reference[index].name}="
        f"{reference[index].quantized_value}@{reference[index].decimal_scale}, candidate {candidate[index].name}="
        f"{candidate[index].quantized_value}@{candidate[index].decimal_scale}"
    )
