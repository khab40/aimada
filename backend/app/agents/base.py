from abc import ABC, abstractmethod

from app.exchange.schemas import Order


class Agent(ABC):
    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    @abstractmethod
    def act(self, timestamp: int) -> list[Order]:
        raise NotImplementedError
