"""Process vs App Scope

Demonstrates:
- EventScope.PROCESS for in-process events (using AsyncQueueBroker)
- EventScope.APP for distributed events (using RedisBroker from FastStream)
- How events are routed to different brokers based on scope

Requirements:
- Redis server running on localhost:6379
- Start Redis with: docker run -d -p 6379:6379 redis
"""
import asyncio
import logging

from eventbus.memory_broker import AsyncQueueBroker
from faststream.redis import RedisBroker
from eventbus.eventbus import EventBus
from eventbus.event import SkyEvent, EventScope


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Demonstrating PROCESS and APP event scopes"""
    print("\n=== Process vs App Scope ===\n")

    # PROCESS scope: in-memory broker for local events
    process_broker = AsyncQueueBroker()

    # APP scope: Redis broker for distributed events
    # Note: Requires Redis server running on localhost:6379
    app_broker = RedisBroker("redis://localhost:6379")

    bus = EventBus(process_broker, app_broker)

    # Process scope event
    class LocalEvent(SkyEvent):
        type: str = "local.event"
        message: str
        scope: EventScope = EventScope.PROCESS

    # App scope event
    class DistributedEvent(SkyEvent):
        type: str = "distributed.event"
        message: str
        scope: EventScope = EventScope.APP

    # Register handlers
    async def handle_local(event_data: dict):
        print(f"  🏠 Local handler: {event_data.get('message')}")

    async def handle_distributed(event_data: dict):
        print(f"  🌐 Distributed handler: {event_data.get('message')}")

    bus.subscribe("local.event", handle_local)
    bus.subscribe("distributed.event", handle_distributed)

    try:
        await bus.start()

        # Publish PROCESS event (through process_level_broker)
        print("  Publishing PROCESS event...")
        local_event = LocalEvent(
            source="local-service",
            message="This is a local event"
        )
        await bus.publish(local_event)

        await asyncio.sleep(0.1)

        # Publish APP event (through app_level_broker)
        print("\n  Publishing APP event...")
        dist_event = DistributedEvent(
            source="distributed-service",
            message="This is a distributed event"
        )
        await bus.publish(dist_event)

        await asyncio.sleep(0.2)
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        print("  💡 Make sure Redis is running: docker run -d -p 6379:6379 redis")
    finally:
        try:
            await bus.stop()
        except Exception:
            pass  # Ignore errors during cleanup


if __name__ == "__main__":
    asyncio.run(main())
