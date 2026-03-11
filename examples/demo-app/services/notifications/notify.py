"""Notification service — sends order confirmations and alerts."""
from dataclasses import dataclass
from enum import Enum


class Channel(Enum):
    EMAIL = "email"
    PUSH = "push"


@dataclass
class Notification:
    recipient_id: str
    channel: Channel
    subject: str
    body: str


_sent: list[Notification] = []


def send_order_confirmation(user_id: str, order_id: str) -> Notification:
    n = Notification(
        recipient_id=user_id,
        channel=Channel.EMAIL,
        subject=f"Order {order_id} confirmed",
        body=f"Your order {order_id} has been placed successfully.",
    )
    _sent.append(n)
    return n


def get_sent_notifications() -> list[Notification]:
    return list(_sent)
