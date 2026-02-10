"""Custom Logger Configuration

Demonstrates:
- Passing custom logger to EventBus
- Configuring logging for EventBus operations
- Using custom logger names and levels
"""
import asyncio
import logging

from eventbus.memory_broker import AsyncQueueBroker
from eventbus.eventbus import EventBus
from eventbus.event import SkyEvent, EventScope


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Using custom logger with EventBus"""
    print("\n=== Custom Logger Configuration ===\n")

    # Create custom logger
    custom_logger = logging.getLogger("my_eventbus")
    custom_logger.setLevel(logging.DEBUG)

    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()

    # Pass custom logger to EventBus
    bus = EventBus(process_broker, app_broker, logger=custom_logger)

    class CustomEvent(SkyEvent):
        type: str = "custom.event"
        data: str
        scope: EventScope = EventScope.PROCESS

    async def handler(event_data: dict):
        print(f"  ✅ Handler executed: {event_data}")

    bus.subscribe("custom.event", handler)

    await bus.start()

    event = CustomEvent(source="custom-service", data="test data")
    await bus.publish(event)

    await asyncio.sleep(0.1)
    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
