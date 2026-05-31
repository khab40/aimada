from abc import ABC, abstractmethod


class Detector(ABC):
    name: str

    @abstractmethod
    def score(self, events: list[dict[str, object]]) -> dict[str, object]:
        raise NotImplementedError
