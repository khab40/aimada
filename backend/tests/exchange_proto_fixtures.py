from app.contracts.generated.lob.exchange.v1 import exchange_pb2


def metadata(sequence: int) -> exchange_pb2.EventMetadata:
    return exchange_pb2.EventMetadata(
        schema_version=1,
        event_id=f"SIM:event:{sequence}",
        sequence=sequence,
        source=exchange_pb2.EVENT_SOURCE_SIMULATION,
        symbol="LOB",
        venue="SIM",
        tick=7,
        scenario_id="scenario-1",
        scenario_name="spoofing_like_wall",
        scenario_family="spoofing_like_wall",
    )


def sample_book() -> exchange_pb2.BookSnapshot:
    return exchange_pb2.BookSnapshot(
        bids=[exchange_pb2.PriceLevel(price_ticks=99, quantity_lots=4, owner="normal")],
        asks=[exchange_pb2.PriceLevel(price_ticks=101, quantity_lots=5, owner="abuser")],
        best_bid_ticks=99,
        best_ask_ticks=101,
        mid_price_ticks_x2=200,
        spread_ticks=2,
    )


def all_event_types() -> list[exchange_pb2.ExchangeEvent]:
    return [
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
            snapshot=exchange_pb2.LobSnapshot(depth=5, book=sample_book()),
        ),
    ]
