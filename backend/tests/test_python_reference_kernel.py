import pytest

from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.hashing import book_hash, event_stream_hash
from app.contracts.python_reference import PythonReferenceKernel, ReferenceKernelError


def request(*, scenario_name: str = "normal_market", max_ticks: int = 4) -> exchange_pb2.SimulationRequest:
    return exchange_pb2.SimulationRequest(
        contract_version=1,
        run_id="PARITY-RUN-001",
        scenario=exchange_pb2.ScenarioInput(
            scenario_id="scenario-1",
            scenario_name=scenario_name,
            scenario_family=scenario_name,
            seed=42,
            max_ticks=max_ticks,
        ),
        config=exchange_pb2.SimulationConfig(
            symbol="BTCUSDT",
            venue="SIM-X",
            price_tick_size_nanos=1_000_000_000,
            quantity_lot_size_nanos=1_000_000,
            snapshot_depth=12,
            max_events=100_000,
            reference_price_ticks=68_125,
            baseline_liquidity_levels=12,
            baseline_liquidity_base_lots=1_500,
            tick_interval_ns=500_000_000,
            normal_agent_count=3,
            baseline_liquidity_tick_size_ticks=1,
            max_agent_quote_lots=25_000,
        ),
    )


def test_python_reference_kernel_is_byte_deterministic_for_same_request() -> None:
    kernel = PythonReferenceKernel()
    simulation_request = request()

    first = kernel.run(simulation_request)
    second = kernel.run(simulation_request)

    assert first.SerializeToString(deterministic=True) == second.SerializeToString(deterministic=True)
    assert first.event_stream_hash == event_stream_hash(first.events)
    assert first.final_book_hash == book_hash(first.final_book)
    assert first.termination_reason == exchange_pb2.TERMINATION_REASON_COMPLETED
    assert [event.metadata.sequence for event in first.events] == list(range(1, len(first.events) + 1))
    assert all(event.metadata.symbol == "BTCUSDT" for event in first.events)
    assert all(event.metadata.venue == "SIM-X" for event in first.events)
    assert [metric.name for metric in first.metrics] == sorted(metric.name for metric in first.metrics)


def test_reference_scenario_emits_all_event_types_and_one_snapshot_per_tick() -> None:
    result = PythonReferenceKernel().run(request(scenario_name="spoofing_like_wall", max_ticks=8))

    payloads = [event.WhichOneof("payload") for event in result.events]
    snapshots = [event for event in result.events if event.WhichOneof("payload") == "snapshot"]

    assert set(payloads) == {"add", "modify", "cancel", "execute", "snapshot"}
    assert [event.metadata.tick for event in snapshots] == list(range(1, 9))
    assert any(event.metadata.scenario_family == "spoofing_like_wall" for event in result.events)


def test_reference_kernel_rejects_unfrozen_parameters_and_resource_overflow() -> None:
    parameterized = request()
    parameterized.scenario.parameters.add(name="wall_lots", integer_value=48)
    with pytest.raises(ReferenceKernelError, match="parameters are not supported"):
        PythonReferenceKernel().run(parameterized)

    constrained = request(max_ticks=1)
    constrained.config.max_events = 1
    with pytest.raises(ReferenceKernelError, match="exceeded configured max_events"):
        PythonReferenceKernel().run(constrained)
