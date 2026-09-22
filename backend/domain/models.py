from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HistoryKey:
    target_date: str
    target_key: str
    item_key: str
    is_waiting: bool = False


@dataclass(frozen=True)
class Availability:
    category: str
    history: HistoryKey
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryResult:
    items: tuple[Availability, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    error: str | None = None


@dataclass(frozen=True)
class DeliveryBatch:
    monitor_id: int
    category: str
    bot_token: str
    chat_id: str
    text: str
    items: tuple[Availability, ...]
