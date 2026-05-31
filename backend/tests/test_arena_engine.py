from app.arena.engine import ArenaEngine


def test_arena_engine_ticks_with_normal_agents_and_book_state() -> None:
    engine = ArenaEngine()

    first = engine.step()
    second = engine.step()

    assert first["tick"] == 1
    assert second["tick"] == 2
    assert second["active_agents"] == ["MM_01", "NOISE_01", "TAKER_01"]
    assert second["book"]["bids"]
    assert second["book"]["asks"]
    assert second["best_bid"] is not None
    assert second["best_ask"] is not None
