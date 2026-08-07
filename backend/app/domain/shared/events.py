"""
Domain Shared Events & Audit Event Interface.

Provides:
- Base class for all domain events
- AuditEvent domain payload structure
- In-process Async Domain Event Bus
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    """Base class for all in-memory domain events."""
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AuditEvent(DomainEvent):
    """
    Structured domain event intended for security auditing and persistence.
    """
    event_type: str = ""  
    actor_type: str = "user"  
    actor_id: UUID | None = None
    workspace_id: UUID | None = None
    organization_id: UUID | None = None
    resource_type: str = ""  
    resource_id: UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None


class DomainEventBus:
    """
    In-process asynchronous event bus for domain event decoupling.
    Allows services to publish events without direct coupling to audit/notification subscribers.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Callable[[DomainEvent], Any]]] = {}

    def subscribe(
        self, event_type: type[DomainEvent], handler: Callable[[DomainEvent], Any]
    ) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        event_cls = type(event)
        handlers = self._subscribers.get(event_cls, [])
        for handler in handlers:
            try:
                res = handler(event)
                if hasattr(res, "__await__"):
                    await res
            except Exception as exc:
                
                import logging
                logging.getLogger("app.domain.events").error(
                    f"Error in event handler {handler.__name__} for {event_cls.__name__}: {exc}"
                )



event_bus = DomainEventBus()
