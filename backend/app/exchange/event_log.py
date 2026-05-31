class EventLog:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def append(self, event: dict[str, object]) -> None:
        self.events.append(event)

    def tail(self, limit: int = 100) -> list[dict[str, object]]:
        return self.events[-limit:]

    def replay_events(self) -> list[dict[str, object]]:
        return list(self.events)
