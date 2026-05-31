from dataclasses import dataclass
from typing import Literal

Side = Literal["buy", "sell"]
OrderType = Literal["limit", "cancel", "market"]


@dataclass(frozen=True)
class Order:
    order_id: str
    agent_id: str
    side: Side
    quantity: int
    price: float | None = None
    order_type: OrderType = "limit"
    timestamp: int = 0
