from app.agents.spoofing_like import SpoofingLikeAgent


def test_spoofing_like_agent_places_large_visible_order() -> None:
    agent = SpoofingLikeAgent("spoof")
    orders = agent.act(1)

    assert orders[0].quantity >= 500
    assert orders[0].side == "buy"
