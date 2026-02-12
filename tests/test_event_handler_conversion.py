"""Test automatic dict-to-object conversion in event_handler decorator"""
import asyncio
import pytest
from opensecflow.eventbus import AsyncQueueBroker
from opensecflow.eventbus.eventbus import init_eventbus, event_handler, event_bus, _pending_handlers
from opensecflow.eventbus.event import ScopedEvent, EventScope


class AutoConversionTestEvent(ScopedEvent):
    """Test event for auto-conversion tests"""
    type: str = "test.autoconversion.event"
    value: int
    scope: EventScope = EventScope.PROCESS


@pytest.fixture
async def eventbus():
    """Create and cleanup EventBus for each test"""
    # Clean up any existing global state
    global event_bus, _pending_handlers
    import opensecflow.eventbus.eventbus as eb_module
    eb_module.event_bus = None
    eb_module._pending_handlers = []

    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()

    bus = init_eventbus(process_broker, app_broker)
    await bus.start()

    yield bus

    await bus.stop()
    # Clean up after test
    eb_module.event_bus = None
    eb_module._pending_handlers = []


@pytest.mark.asyncio
async def test_event_handler_receives_typed_object(eventbus):
    """Test that event_handler decorator converts dict to typed event object"""
    received_events = []

    @event_handler(AutoConversionTestEvent)
    async def handler(event: AutoConversionTestEvent):
        # Verify it's the correct type
        assert isinstance(event, AutoConversionTestEvent)
        assert event.value == 42
        received_events.append(event)

    # Publish event
    test_event = AutoConversionTestEvent(
        type="test.autoconversion.event",
        value=42,
        source="test",
        scope=EventScope.PROCESS
    )
    await eventbus.publish(test_event)
    await asyncio.sleep(0.1)  # Allow processing

    # Verify handler received the event
    assert len(received_events) == 1
    assert isinstance(received_events[0], AutoConversionTestEvent)
    assert received_events[0].value == 42


@pytest.mark.asyncio
async def test_event_handler_with_multiple_events(eventbus):
    """Test that handler correctly processes multiple events"""
    received_values = []

    @event_handler(AutoConversionTestEvent)
    async def handler(event: AutoConversionTestEvent):
        assert isinstance(event, AutoConversionTestEvent)
        received_values.append(event.value)

    # Publish multiple events
    for value in [10, 20, 30]:
        test_event = AutoConversionTestEvent(
            type="test.autoconversion.event",
            value=value,
            source="test",
            scope=EventScope.PROCESS
        )
        await eventbus.publish(test_event)

    await asyncio.sleep(0.2)  # Allow processing

    # Verify all events were received
    assert len(received_values) == 3
    assert received_values == [10, 20, 30]


@pytest.mark.asyncio
async def test_type_safety_with_attributes(eventbus):
    """Test that event attributes are properly typed and accessible"""

    class DetailedEvent(ScopedEvent):
        type: str = "test.detailed.event"
        order_id: str
        amount: float
        items: list
        scope: EventScope = EventScope.PROCESS

    received_event = None

    @event_handler(DetailedEvent)
    async def handler(event: DetailedEvent):
        nonlocal received_event
        received_event = event
        # Verify type safety - these attributes must exist and have correct types
        assert isinstance(event.order_id, str)
        assert isinstance(event.amount, float)
        assert isinstance(event.items, list)

    # Publish detailed event
    test_event = DetailedEvent(
        type="test.detailed.event",
        order_id="ORD-123",
        amount=99.99,
        items=["item1", "item2"],
        source="test",
        scope=EventScope.PROCESS
    )
    await eventbus.publish(test_event)
    await asyncio.sleep(0.1)

    # Verify event was received and properties are accessible
    assert received_event is not None
    assert received_event.order_id == "ORD-123"
    assert received_event.amount == 99.99
    assert len(received_event.items) == 2
