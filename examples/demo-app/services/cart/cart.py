"""Cart service — session-scoped shopping cart."""
from dataclasses import dataclass, field


@dataclass
class CartItem:
    book_id: str
    quantity: int = 1


@dataclass
class Cart:
    user_id: str
    items: list[CartItem] = field(default_factory=list)

    def add(self, book_id: str, qty: int = 1) -> None:
        for item in self.items:
            if item.book_id == book_id:
                item.quantity += qty
                return
        self.items.append(CartItem(book_id, qty))

    def remove(self, book_id: str) -> None:
        self.items = [i for i in self.items if i.book_id != book_id]

    def clear(self) -> None:
        self.items.clear()

    @property
    def total_items(self) -> int:
        return sum(i.quantity for i in self.items)


# In-memory session store
_carts: dict[str, Cart] = {}


def get_cart(user_id: str) -> Cart:
    if user_id not in _carts:
        _carts[user_id] = Cart(user_id)
    return _carts[user_id]
