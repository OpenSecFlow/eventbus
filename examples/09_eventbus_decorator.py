"""EventBus with Decorator Registration

Demonstrates:
- Using @event_handler decorator for handler registration
- Global EventBus initialization with init_eventbus()
- Multiple handlers for the same event type
- APP scope events
"""
import asyncio
import logging

from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from opensecflow.eventbus.eventbus import event_handler, init_eventbus
from opensecflow.eventbus.event import ScopedEvent, EventScope


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Using @event_handler decorator for registration"""
    print("\n=== EventBus with Decorator Registration ===\n")

    # Define event class
    class UserRegisteredEvent(ScopedEvent):
        type: str = "user.registered"
        user_id: str
        email: str
        scope: EventScope = EventScope.APP

    # Use decorator to register handlers
    @event_handler(UserRegisteredEvent)
    async def send_welcome_email(event_data: dict):
        print(f"  📧 Sending welcome email to: {event_data.get('email')}")

    @event_handler(UserRegisteredEvent)
    async def create_user_profile(event_data: dict):
        print(f"  👤 Creating profile for user: {event_data.get('user_id')}")

    # Initialize global EventBus
    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()
    bus = init_eventbus(process_broker, app_broker)

    await bus.start()

    # Publish event
    event = UserRegisteredEvent(
        source="user-service",
        user_id="U-001",
        email="user@example.com"
    )
    await bus.publish(event)

    await asyncio.sleep(0.2)
    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
