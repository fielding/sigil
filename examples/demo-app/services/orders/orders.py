"""Order service — processes checkout and tracks orders."""
from dataclasses import dataclass, field
from enum import Enum
import uuid


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class OrderLine:
    book_id: str
    quantity: int
    price_cents: int


@dataclass
class Order:
    id: str
    user_id: str
    lines: list[OrderLine]
    status: OrderStatus = OrderStatus.PENDING
    total_cents: int = 0

    def __post_init__(self):
        self.total_cents = sum(l.price_cents * l.quantity for l in self.lines)


_orders: dict[str, Order] = {}


def create_order(user_id: str, lines: list[OrderLine]) -> Order:
    order = Order(id=f"ord-{uuid.uuid4().hex[:8]}", user_id=user_id, lines=lines)
    _orders[order.id] = order
    return order


def get_order(order_id: str) -> Order | None:
    return _orders.get(order_id)


def list_user_orders(user_id: str) -> list[Order]:
    return [o for o in _orders.values() if o.user_id == user_id]
