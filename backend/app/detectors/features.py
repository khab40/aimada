def count_events(events: list[dict[str, object]], event_type: str) -> int:
    return sum(1 for event in events if event.get("type") == event_type)


def max_quantity(events: list[dict[str, object]]) -> int:
    quantities = [int(event.get("quantity", 0)) for event in events]
    return max(quantities, default=0)


def unique_price_levels(events: list[dict[str, object]]) -> int:
    return len({event.get("price") for event in events if event.get("price") is not None})
