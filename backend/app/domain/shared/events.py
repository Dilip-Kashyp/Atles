"""
Domain Shared Events & Audit Event Interface.

Provides:
- Base class for all domain events
- AuditEvent domain payload structure
- In-process Async Domain Event Bus
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type
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
    event_type: str = ""  # e.g., 'UserCreated', 'OAuthLinked', 'WorkspaceCreated'
    actor_type: str = "user"  # 'user' | 'service_account' | 'system' | 'api_key'
    actor_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    resource_type: str = ""  # 'user' | 'workspace' | 'organization' | 'session' | 'api_key'
    resource_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


class DomainEventBus:
    """
    In-process asynchronous event bus for domain event decoupling.
    Allows services to publish events without direct coupling to audit/notification subscribers.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[Type[DomainEvent], List[Callable[[DomainEvent], Any]]] = {}

    def subscribe(
        self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], Any]
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
                # Event handler errors MUST NOT break business transactions
                import logging
                logging.getLogger("app.domain.events").error(
                    f"Error in event handler {handler.__name__} for {event_cls.__name__}: {exc}"
                )


# Global singleton event bus
event_bus = DomainEventBus()
