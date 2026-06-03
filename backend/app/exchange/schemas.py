from dataclasses import dataclass
from typing import Literal

Side = Literal["buy", "sell"]
BookSide = Literal["bid", "ask"]
OrderType = Literal["limit", "cancel", "market"]


@dataclass(frozen=True)
class Order:
    order_id: str
    agent_id: str
    side: Side
    quantity: float
    price: float | None = None
    order_type: OrderType = "limit"
    timestamp: int = 0
    scenario_id: str | None = None
    scenario_name: str | None = None
    scenario_family: str | None = None


@dataclass(frozen=True)
class PriceLevel:
    price: float
    quantity: float
    owner: str | None = None

    def to_dict(self) -> dict[str, float | str]:
        data: dict[str, float | str] = {"price": self.price, "quantity": self.quantity}
        if self.owner and self.owner != "normal":
            data["owner"] = self.owner
        return data


@dataclass(frozen=True)
class OrderBookSnapshot:
    bids: list[PriceLevel]
    asks: list[PriceLevel]
    best_bid: float | None
    best_ask: float | None
    mid: float | None
    spread: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "mid": self.mid,
            "spread": self.spread,
        }
