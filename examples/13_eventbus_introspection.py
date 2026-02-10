"""Handler Introspection

Demonstrates:
- Using get_handlers() to inspect registered handlers
- Viewing handler metadata (function name, module)
- Understanding what handlers are registered for each event type
"""
import asyncio
import logging

from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from opensecflow.eventbus.eventbus import EventBus
from opensecflow.eventbus.event import ScopedEvent, EventScope


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Inspecting registered handlers"""
    print("\n=== Handler Introspection ===\n")

    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()
    bus = EventBus(process_broker, app_broker)

    class TestEvent(ScopedEvent):
        type: str = "test.event"
        scope: EventScope = EventScope.PROCESS

    async def handler1(event_data: dict):
        pass

    async def handler2(event_data: dict):
        pass

    bus.subscribe("test.event", handler1)
    bus.subscribe("test.event", handler2)
    bus.subscribe("another.event", handler1)

    # Get all handlers
    handlers = bus.get_handlers()
    print("  Registered handlers:")
    for event_type, handler_list in handlers.items():
        print(f"    {event_type}:")
        for handler_info in handler_list:
            print(f"      - {handler_info['function_name']} ({handler_info['module']})")


if __name__ == "__main__":
    asyncio.run(main())
