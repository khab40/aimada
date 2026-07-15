from app.agents.layering_like import LayeringLikeAgent
from app.agents.quote_stuffing import QuoteStuffingAgent
from app.agents.spoofing_like import SpoofingLikeAgent
from app.arena.engine import ArenaEngine


def test_spoofing_like_agent_places_and_cancels_labeled_wall() -> None:
    agent = SpoofingLikeAgent("ABUSER_01", scenario_id="scenario-1")

    first = agent.act(10)
    agent.act(11)
    agent.act(12)
    fourth = agent.act(13)

    assert first[0].scenario_id == "scenario-1"
    assert first[0].scenario_name == "spoofing_like_wall"
    assert first[0].quantity == 480
    assert fourth[0].order_type == "cancel"
    assert fourth[0].order_id == first[0].order_id


def test_layering_like_agent_emits_multiple_labeled_levels() -> None:
    agent = LayeringLikeAgent("ABUSER_02", scenario_id="scenario-2")

    orders = agent.act(20)

    assert len(orders) == 4
    assert {order.scenario_family for order in orders} == {"layering_like"}
    assert len({order.price for order in orders}) == 4


def test_quote_stuffing_agent_emits_place_cancel_burst() -> None:
    agent = QuoteStuffingAgent("ABUSER_03", scenario_id="scenario-3")

    first = agent.act(30)
    second = agent.act(31)

    assert len(first) == 12
    assert len(second) == 24
    assert any(order.order_type == "cancel" for order in second)
    assert {order.scenario_family for order in second} == {"quote_stuffing"}


def test_arena_engine_launches_scenario_with_labeled_events() -> None:
    engine = ArenaEngine()

    result = engine.launch_scenario("spoofing_like_wall")
    state = engine.step()

    assert result["accepted"] is True
    assert state["active_scenario"]["scenario_name"] == "spoofing_like_wall"
    assert "ABUSER_01" in state["active_agents"]
    assert any(event.get("scenario_family") == "spoofing_like_wall" for event in state["events"])
