"""Multiple Handlers for Same Event

Demonstrates:
- Multiple handlers subscribing to the same event type
- Fan-out pattern where one event triggers multiple handlers
- All handlers execute when event is published
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
    """Multiple handlers for the same event"""
    print("\n=== Multiple Handlers for Same Event ===\n")

    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()

    class OrderShippedEvent(ScopedEvent):
        type: str = "order.shipped"
        order_id: str
        tracking_number: str
        scope: EventScope = EventScope.APP

    async def send_notification(event_data: dict):
        print(f"  📱 Sending notification for order: {event_data.get('order_id')}")

    async def update_inventory(event_data: dict):
        print(f"  📦 Updating inventory for order: {event_data.get('order_id')}")

    async def log_shipment(event_data: dict):
        print(f"  📝 Logging shipment: {event_data.get('tracking_number')}")

    async with EventBus(process_broker, app_broker) as bus:
        # Register multiple handlers
        bus.subscribe("order.shipped", send_notification)
        bus.subscribe("order.shipped", update_inventory)
        bus.subscribe("order.shipped", log_shipment)

        # Publish event - all handlers will be called
        event = OrderShippedEvent(
            source="shipping-service",
            order_id="ORD-002",
            tracking_number="TRK-123456"
        )
        await bus.publish(event)

        await asyncio.sleep(0.2)


if __name__ == "__main__":
    asyncio.run(main())
