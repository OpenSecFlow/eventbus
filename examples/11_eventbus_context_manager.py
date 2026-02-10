"""EventBus with Context Manager

Demonstrates:
- Using async with EventBus() for automatic lifecycle management
- Clean resource management pattern
- Automatic start/stop handling
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
    """Using async with for automatic lifecycle management"""
    print("\n=== EventBus with Context Manager ===\n")

    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()

    class PaymentEvent(ScopedEvent):
        type: str = "payment.completed"
        payment_id: str
        amount: float
        scope: EventScope = EventScope.APP

    async def handle_payment(event_data: dict):
        print(f"  💰 Payment processed: {event_data}")

    # Use context manager
    async with EventBus(process_broker, app_broker) as bus:
        bus.subscribe("payment.completed", handle_payment)

        event = PaymentEvent(
            source="payment-service",
            payment_id="PAY-001",
            amount=199.99
        )
        await bus.publish(event)

        await asyncio.sleep(0.1)

    print("  EventBus stopped automatically")


if __name__ == "__main__":
    asyncio.run(main())
