"""Basic EventBus Usage

Demonstrates:
- Creating EventBus with process and app brokers
- Direct subscription and publishing
- Basic event handling with PROCESS scope
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
    """Basic EventBus publish-subscribe example"""
    print("\n=== Basic EventBus Usage ===\n")

    # Create two brokers
    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()

    # Create EventBus
    bus = EventBus(process_broker, app_broker)

    # Define event class
    class OrderCreatedEvent(SkyEvent):
        type: str = "order.created"
        order_id: str
        amount: float
        scope: EventScope = EventScope.PROCESS

    # Define handler function
    async def handle_order(event_data: dict):
        print(f"  📦 Received order: ID={event_data.get('order_id')}, Amount={event_data.get('amount')}")

    # Subscribe to event
    bus.subscribe("order.created", handle_order)

    # Start EventBus
    await bus.start()

    # Publish event
    print("  Publishing order event...")
    event = OrderCreatedEvent(
        source="order-service",
        order_id="ORD-001",
        amount=99.9
    )
    await bus.publish(event)

    # Wait for event processing
    await asyncio.sleep(0.5)
    print("  Event processing complete")

    await bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
