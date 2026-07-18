from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from scripts.generate_protos import check_generated


def metadata(sequence: int) -> exchange_pb2.EventMetadata:
    return exchange_pb2.EventMetadata(
        schema_version=1,
        event_id=f"SIM:event:{sequence}",
        sequence=sequence,
        source=exchange_pb2.EVENT_SOURCE_SIMULATION,
        symbol="LOB",
        venue="SIM",
        tick=7,
    )


def test_generated_bindings_are_current() -> None:
    assert check_generated()


def test_contract_has_stable_package_and_java_generation_options() -> None:
    descriptor = exchange_pb2.DESCRIPTOR

    assert descriptor.package == "lob.exchange.v1"
    assert descriptor.GetOptions().java_package == "ai.lobarena.exchange.v1"
    assert descriptor.GetOptions().java_multiple_files is True


def test_all_exchange_event_payloads_round_trip_with_oneof_discriminator() -> None:
    events = [
        exchange_pb2.ExchangeEvent(
            metadata=metadata(1),
            add=exchange_pb2.AddOrder(
                order_id="o1",
                agent_id="maker",
                side=exchange_pb2.SIDE_BUY,
                price_ticks=99,
                quantity_lots=5,
                owner="normal",
            ),
        ),
        exchange_pb2.ExchangeEvent(
            metadata=metadata(2),
            modify=exchange_pb2.ModifyOrder(
                order_id="o1",
                agent_id="maker",
                side=exchange_pb2.SIDE_BUY,
                previous_price_ticks=99,
                previous_quantity_lots=5,
                price_ticks=100,
                quantity_lots=4,
                priority_preserved=False,
                owner="normal",
            ),
        ),
        exchange_pb2.ExchangeEvent(
            metadata=metadata(3),
            cancel=exchange_pb2.CancelOrder(
                order_id="o1",
                agent_id="maker",
                side=exchange_pb2.SIDE_BUY,
                price_ticks=100,
                quantity_lots=4,
                owner="normal",
            ),
        ),
        exchange_pb2.ExchangeEvent(
            metadata=metadata(4),
            execute=exchange_pb2.ExecuteOrder(
                execution_id="x1",
                aggressor_order_id="buy-1",
                resting_order_id="sell-1",
                aggressor_agent_id="taker",
                resting_agent_id="maker",
                aggressor_side=exchange_pb2.SIDE_BUY,
                price_ticks=101,
                quantity_lots=2,
                aggressor_remaining_quantity_lots=0,
                resting_remaining_quantity_lots=3,
            ),
        ),
        exchange_pb2.ExchangeEvent(
            metadata=metadata(5),
            snapshot=exchange_pb2.LobSnapshot(
                depth=5,
                book=exchange_pb2.BookSnapshot(
                    bids=[exchange_pb2.PriceLevel(price_ticks=99, quantity_lots=4)],
                    asks=[exchange_pb2.PriceLevel(price_ticks=101, quantity_lots=5)],
                    best_bid_ticks=99,
                    best_ask_ticks=101,
                    mid_price_ticks_x2=200,
                    spread_ticks=2,
                ),
            ),
        ),
    ]

    decoded = [exchange_pb2.ExchangeEvent.FromString(event.SerializeToString()) for event in events]

    assert [event.WhichOneof("payload") for event in decoded] == ["add", "modify", "cancel", "execute", "snapshot"]
    assert [event.metadata.sequence for event in decoded] == [1, 2, 3, 4, 5]
    assert decoded[-1].snapshot.book.mid_price_ticks_x2 == 200


def test_simulation_request_and_result_round_trip_without_maps_or_floats() -> None:
    request = exchange_pb2.SimulationRequest(
        contract_version=1,
        run_id="RUN-000001",
        scenario=exchange_pb2.ScenarioInput(
            scenario_id="scenario-1",
            scenario_name="spoofing_like_wall",
            scenario_family="spoofing_like_wall",
            seed=42,
            max_ticks=10,
            parameters=[exchange_pb2.ScenarioParameter(name="wall_lots", integer_value=48)],
        ),
        config=exchange_pb2.SimulationConfig(
            symbol="LOB",
            venue="SIM",
            price_tick_size_nanos=1_000_000_000,
            quantity_lot_size_nanos=1_000_000,
            snapshot_depth=12,
            max_events=10_000,
            reference_price_ticks=68_125,
            baseline_liquidity_levels=12,
            baseline_liquidity_base_lots=1_500,
        ),
    )
    result = exchange_pb2.SimulationResult(
        contract_version=1,
        run_id=request.run_id,
        metrics=[exchange_pb2.MetricValue(name="f1", quantized_value=925_000, decimal_scale=6)],
        event_stream_hash=b"event-hash",
        final_book_hash=b"book-hash",
        termination_reason=exchange_pb2.TERMINATION_REASON_COMPLETED,
    )

    decoded_request = exchange_pb2.SimulationRequest.FromString(request.SerializeToString())
    decoded_result = exchange_pb2.SimulationResult.FromString(result.SerializeToString())

    assert decoded_request == request
    assert decoded_result == result
    assert decoded_request.scenario.parameters[0].WhichOneof("value") == "integer_value"
    assert all(not field.message_type or not field.message_type.GetOptions().map_entry for field in request.DESCRIPTOR.fields)
