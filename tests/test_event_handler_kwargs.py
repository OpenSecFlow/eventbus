"""Test wrapper handles both positional and keyword arguments"""
import asyncio
import pytest
from opensecflow.eventbus import AsyncQueueBroker
from opensecflow.eventbus.eventbus import init_eventbus, event_handler
from opensecflow.eventbus.event import ScopedEvent, EventScope


class KeywordTestEvent(ScopedEvent):
    """Test event for keyword argument handling"""
    type: str = "test.keyword.event"
    value: int
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
async def test_handler_with_positional_argument(eventbus):
    """Test that handler works with positional argument (normal EventBus usage)"""
    received_values = []

    @event_handler(KeywordTestEvent)
    async def handler(event: KeywordTestEvent):
        assert isinstance(event, KeywordTestEvent)
        received_values.append(event.value)

    # Publish event through EventBus (normal usage)
    test_event = KeywordTestEvent(
        type="test.keyword.event",
        value=123,
        source="test",
        scope=EventScope.PROCESS
    )
    await eventbus.publish(test_event)
    await asyncio.sleep(0.1)

    assert len(received_values) == 1
    assert received_values[0] == 123


@pytest.mark.asyncio
async def test_wrapper_accepts_dict_as_positional_arg():
    """Test that wrapper can accept dict as positional argument"""
    import opensecflow.eventbus.eventbus as eb_module
    eb_module.event_bus = None
    eb_module._pending_handlers = []

    received_event = None

    @event_handler(KeywordTestEvent)
    async def handler(event: KeywordTestEvent):
        nonlocal received_event
        received_event = event

    # Get the wrapper function
    wrapper = handler

    # Call wrapper with dict as positional argument
    test_dict = {
        "type": "test.keyword.event",
        "value": 456,
        "source": "test"
    }

    await wrapper(test_dict)

    assert received_event is not None
    assert isinstance(received_event, KeywordTestEvent)
    assert received_event.value == 456


@pytest.mark.asyncio
async def test_wrapper_accepts_dict_as_keyword_arg():
    """Test that wrapper can accept dict as keyword argument (FastStream compatibility)"""
    import opensecflow.eventbus.eventbus as eb_module
    eb_module.event_bus = None
    eb_module._pending_handlers = []

    received_event = None

    @event_handler(KeywordTestEvent)
    async def handler(event: KeywordTestEvent):
        nonlocal received_event
        received_event = event

    # Get the wrapper function
    wrapper = handler

    # Call wrapper with dict as keyword argument (how FastStream might call it)
    test_dict = {
        "type": "test.keyword.event",
        "value": 789,
        "source": "test"
    }

    await wrapper(event=test_dict)

    assert received_event is not None
    assert isinstance(received_event, KeywordTestEvent)
    assert received_event.value == 789


@pytest.mark.asyncio
async def test_wrapper_accepts_event_object():
    """Test that wrapper can accept already-instantiated event object"""
    import opensecflow.eventbus.eventbus as eb_module
    eb_module.event_bus = None
    eb_module._pending_handlers = []

    received_event = None

    @event_handler(KeywordTestEvent)
    async def handler(event: KeywordTestEvent):
        nonlocal received_event
        received_event = event

    # Get the wrapper function
    wrapper = handler

    # Call wrapper with event object (backward compatibility)
    test_event = KeywordTestEvent(
        type="test.keyword.event",
        value=999,
        source="test"
    )

    await wrapper(test_event)

    assert received_event is not None
    assert isinstance(received_event, KeywordTestEvent)
    assert received_event.value == 999
