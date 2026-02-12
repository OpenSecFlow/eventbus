"""Test type safety benefits with event_handler decorator"""
import asyncio
import pytest
from opensecflow.eventbus import AsyncQueueBroker
from opensecflow.eventbus.eventbus import init_eventbus, event_handler
from opensecflow.eventbus.event import ScopedEvent, EventScope


class OrderCreatedEvent(ScopedEvent):
    """Order created event with full type annotations"""
    type: str = "order.created"
    order_id: str
    customer_name: str
    amount: float
    items: list
    scope: EventScope = EventScope.PROCESS


class PaymentProcessedEvent(ScopedEvent):
    """Payment processed event"""
    type: str = "payment.processed"
    payment_id: str
    order_id: str
    amount: float
    method: str
    scope: EventScope = EventScope.PROCESS


@pytest.fixture
async def eventbus():
    """Create and cleanup EventBus for each test"""
    import opensecflow.eventbus.eventbus as eb_module
    eb_module.event_bus = None
    eb_module._pending_handlers = []

    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()

    bus = init_eventbus(process_broker, app_broker)
    await bus.start()

    yield bus

    await bus.stop()
    eb_module.event_bus = None
    eb_module._pending_handlers = []


@pytest.mark.asyncio
async def test_order_created_handler_type_safety(eventbus):
    """Test that OrderCreatedEvent handler receives fully typed object"""
    received_event = None

    @event_handler(OrderCreatedEvent)
    async def handle_order_created(event: OrderCreatedEvent):
        nonlocal received_event
        received_event = event
        # Type safety: these properties are guaranteed to exist and have correct types
        assert isinstance(event.order_id, str)
        assert isinstance(event.customer_name, str)
        assert isinstance(event.amount, float)
        assert isinstance(event.items, list)

    # Publish order event
    order_event = OrderCreatedEvent(
        source="order-service",
        order_id="ORD-12345",
        customer_name="Alice Smith",
        amount=299.99,
        items=["Laptop", "Mouse", "Keyboard"]
    )
    await eventbus.publish(order_event)
    await asyncio.sleep(0.1)

    # Verify event was received with correct data
    assert received_event is not None
    assert received_event.order_id == "ORD-12345"
    assert received_event.customer_name == "Alice Smith"
    assert received_event.amount == 299.99
    assert len(received_event.items) == 3


@pytest.mark.asyncio
async def test_payment_processed_handler_type_safety(eventbus):
    """Test that PaymentProcessedEvent handler receives fully typed object"""
    received_event = None

    @event_handler(PaymentProcessedEvent)
    async def handle_payment_processed(event: PaymentProcessedEvent):
        nonlocal received_event
        received_event = event
        # Type safety in action
        assert isinstance(event.payment_id, str)
        assert isinstance(event.order_id, str)
        assert isinstance(event.amount, float)
        assert isinstance(event.method, str)

    # Publish payment event
    payment_event = PaymentProcessedEvent(
        source="payment-service",
        payment_id="PAY-67890",
        order_id="ORD-12345",
        amount=299.99,
        method="credit_card"
    )
    await eventbus.publish(payment_event)
    await asyncio.sleep(0.1)

    # Verify event was received with correct data
    assert received_event is not None
    assert received_event.payment_id == "PAY-67890"
    assert received_event.order_id == "ORD-12345"
    assert received_event.amount == 299.99
    assert received_event.method == "credit_card"


@pytest.mark.asyncio
async def test_multiple_event_types_independently(eventbus):
    """Test that different event types are handled independently with type safety"""
    order_events = []
    payment_events = []

    @event_handler(OrderCreatedEvent)
    async def handle_order(event: OrderCreatedEvent):
        assert isinstance(event, OrderCreatedEvent)
        order_events.append(event)

    @event_handler(PaymentProcessedEvent)
    async def handle_payment(event: PaymentProcessedEvent):
        assert isinstance(event, PaymentProcessedEvent)
        payment_events.append(event)

    # Publish both event types
    order = OrderCreatedEvent(
        source="order-service",
        order_id="ORD-001",
        customer_name="Bob",
        amount=100.0,
        items=["Item1"]
    )
    payment = PaymentProcessedEvent(
        source="payment-service",
        payment_id="PAY-001",
        order_id="ORD-001",
        amount=100.0,
        method="paypal"
    )

    await eventbus.publish(order)
    await eventbus.publish(payment)
    await asyncio.sleep(0.1)

    # Verify both handlers received their respective events
    assert len(order_events) == 1
    assert len(payment_events) == 1
    assert order_events[0].order_id == "ORD-001"
    assert payment_events[0].payment_id == "PAY-001"


@pytest.mark.asyncio
async def test_event_attribute_access_without_dict_checks(eventbus):
    """Test that handler can access event attributes directly without dict.get()"""

    @event_handler(OrderCreatedEvent)
    async def handle_order(event: OrderCreatedEvent):
        # Direct attribute access - no need for dict.get() or key checking
        # This demonstrates the benefit of automatic dict-to-object conversion
        order_summary = f"Order {event.order_id} for {event.customer_name}: ${event.amount:.2f}"
        assert "ORD" in order_summary
        assert "Alice" in order_summary
        assert "299.99" in order_summary

        # Can use list operations directly
        item_count = len(event.items)
        assert item_count == 2

    order = OrderCreatedEvent(
        source="test",
        order_id="ORD-999",
        customer_name="Alice",
        amount=299.99,
        items=["Item1", "Item2"]
    )
    await eventbus.publish(order)
    await asyncio.sleep(0.1)
