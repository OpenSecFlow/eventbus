"""EventBus Package

Provides two messaging approaches:
1. AsyncQueueBroker - FastStream API-compatible in-memory broker (recommended)
2. EventBus - Original event bus implementation
"""

from .eventbus import EventBus
from .event import CloudEvent, EventScope, ScopedEvent
from .memory_broker import AsyncQueueBroker

__all__ = [
    "EventBus",
    "CloudEvent",
    "EventScope",
    "ScopedEvent",
    "AsyncQueueBroker",
]
