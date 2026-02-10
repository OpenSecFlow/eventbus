# EventBus

A Python event bus library based on the CloudEvents specification, supporting in-process and distributed event handling.

## Features

- **CloudEvents Specification**: Full implementation of CloudEvents v1.0 specification
- **Dual-Mode Event Handling**:
  - PROCESS scope: Fast in-process event handling
  - APP scope: Distributed event distribution across instances
- **FastStream Compatible**: Provides memory broker compatible with FastStream API
- **RPC Support**: Built-in request-response pattern
- **FastAPI Integration**: Seamless integration with FastAPI applications
- **Decorator Pattern**: Clean event handler registration
- **Statistics and Introspection**: Built-in event statistics and handler query functionality

## Installation

```bash
# Install with uv (recommended)
uv pip install -e .

# Install with optional dependencies for examples
uv pip install -e ".[examples]"

# Install with Redis support for distributed events
uv pip install -e ".[redis]"

# Or install core dependencies only
pip install pydantic faststream
```

## Quick Start

### Basic Usage

```python
import asyncio
from eventbus.memory_broker import AsyncQueueBroker
from eventbus.eventbus import EventBus
from eventbus.event import SkyEvent, EventScope

# Create brokers (both using AsyncQueueBroker for simplicity)
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
    print(f"Processing order: {event_data['order_id']}")

# Subscribe to event
bus.subscribe("order.created", handle_order)

# Start EventBus
await bus.start()

# Publish event
event = OrderCreatedEvent(
    source="order-service",
    order_id="ORD-001",
    amount=99.9
)
await bus.publish(event)

# Stop EventBus
await bus.stop()
```

### FastAPI Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from eventbus.memory_broker import AsyncQueueBroker
from eventbus.eventbus import init_eventbus, event_handler
from eventbus.event import SkyEvent, EventScope

# Define event
class OrderCreatedEvent(SkyEvent):
    type: str = "order.created"
    order_id: str
    scope: EventScope = EventScope.PROCESS

# Register handler using decorator
@event_handler(OrderCreatedEvent)
async def handle_order(event_data: dict):
    print(f"Processing order: {event_data['order_id']}")

# FastAPI lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()
    event_bus = init_eventbus(process_broker, app_broker)
    app.state.event_bus = event_bus
    await event_bus.start()
    yield
    await event_bus.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/orders")
async def create_order(order_id: str, amount: float):
    event = OrderCreatedEvent(
        source="api",
        order_id=order_id,
        amount=amount
    )
    await app.state.event_bus.publish(event)
    return {"status": "created"}
```

### Distributed Setup (Optional)

For distributed event handling across multiple instances, use FastStream brokers:

```python
from eventbus.memory_broker import AsyncQueueBroker
from faststream.redis import RedisBroker
from eventbus.eventbus import EventBus

# Process broker: in-memory for fast local events
process_broker = AsyncQueueBroker()

# App broker: Redis for distributed events across instances
app_broker = RedisBroker("redis://localhost:6379")

bus = EventBus(process_broker, app_broker)
```

**Note**: Redis support requires the `[redis]` extra: `pip install -e ".[redis]"`. For single-instance applications, you can use `AsyncQueueBroker` for both brokers.

## Core Concepts

### CloudEvent

Event class based on [CloudEvents v1.0 specification](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md).

**Required Attributes**:
- `id`: Event unique identifier (auto-generated UUID)
- `source`: Event source identifier (URI-reference format)
- `specversion`: CloudEvents specification version (default "1.0")
- `type`: Event type identifier

**Optional Attributes**:
- `datacontenttype`: Data content type (default "application/json")
- `dataschema`: Data schema URI
- `subject`: Event subject
- `time`: Event timestamp (auto-generated)
- `data`: Event payload data
- `extensions`: Extension attributes dictionary

### SkyEvent

Extends CloudEvent with event scope functionality.

**Additional Attributes**:
- `scope`: Event scope (EventScope.PROCESS or EventScope.APP)

**EventScope Explanation**:
- `PROCESS`: In-process events, handled only in current instance, uses memory queue, fast response
- `APP`: Application-level events, distributed to all instances via broker (e.g., Redis)

### AsyncQueueBroker

FastStream API-compatible memory broker, suitable for:
- Development and testing environments
- Single-process applications
- Scenarios without Redis requirement

**Main Methods**:
- `subscriber(channel)`: Create subscriber decorator
- `publisher(channel)`: Create publisher decorator
- `publish(message, channel)`: Publish message
- `request(message, channel, timeout)`: RPC request
- `start()` / `stop()`: Start/stop broker
- `get_stats()`: Get statistics
- `get_subscribers()`: Get subscriber information

### EventBus

Event bus core class, manages event subscription and publishing.

**Main Methods**:
- `subscribe(event_type, handler)`: Register event handler
- `publish(event)`: Publish event
- `start()` / `stop()`: Start/stop event bus
- `get_handlers()`: Get all registered handlers

**Decorators**:
- `@event_handler(EventClass)`: Auto-register event handler

## Usage Examples

### 1. Basic Pub/Sub

```python
from eventbus.memory_broker import AsyncQueueBroker

broker = AsyncQueueBroker()

@broker.subscriber("events.user.created")
async def handle_user(data: dict):
    print(f"New user: {data['username']}")

await broker.start()
await broker.publish({"username": "alice"}, channel="events.user.created")
await broker.stop()
```

### 2. Multiple Subscribers

```python
@broker.subscriber("events.order.created")
async def send_email(data: dict):
    print(f"Sending email: Order {data['order_id']}")

@broker.subscriber("events.order.created")
async def update_inventory(data: dict):
    print(f"Updating inventory: Order {data['order_id']}")

await broker.publish({"order_id": "123"}, channel="events.order.created")
```

### 3. Publisher Decorator

```python
@broker.publisher("events.result")
async def process_data(data: dict) -> dict:
    # Return value automatically published to events.result
    return {"status": "processed", "data": data}

@broker.subscriber("events.result")
async def handle_result(data: dict):
    print(f"Result: {data}")

await process_data({"value": 42})
```

### 4. RPC Pattern

```python
@broker.subscriber("rpc.calculate")
async def calculate(data: dict) -> dict:
    result = data["a"] + data["b"]
    return {"result": result}

# Send request and wait for response
response = await broker.request(
    {"a": 10, "b": 20},
    channel="rpc.calculate",
    timeout=1.0
)
print(response)  # {"result": 30}
```

### 5. Context Manager

```python
async with AsyncQueueBroker() as broker:
    @broker.subscriber("events.test")
    async def handler(data: dict):
        print(data)

    await broker.publish({"msg": "hello"}, channel="events.test")
    await asyncio.sleep(0.1)
```

### 6. Event Scopes

```python
# In-process event (fast)
process_event = SkyEvent(
    type="cache.cleared",
    source="cache-service",
    scope=EventScope.PROCESS,
    data={"cache_key": "user_123"}
)
await bus.publish(process_event)

# Application-level event (distributed)
app_event = SkyEvent(
    type="user.registered",
    source="auth-service",
    scope=EventScope.APP,
    data={"user_id": "456"}
)
await bus.publish(app_event)
```

### 7. Statistics

```python
stats = broker.get_stats()
print(f"Published: {stats['published']}")
print(f"Consumed: {stats['consumed']}")
print(f"Errors: {stats['errors']}")
print(f"Channels: {stats['channels']}")
print(f"Subscribers: {stats['subscribers']}")
```

### 8. Handler Introspection

```python
handlers = bus.get_handlers()
for event_type, handler_list in handlers.items():
    print(f"{event_type}:")
    for h in handler_list:
        print(f"  - {h['function_name']} ({h['module']})")
```

## Example Files

The [examples](examples/) directory contains complete example code:

### AsyncQueueBroker Examples
- [01_basic_pubsub.py](examples/01_basic_pubsub.py) - Basic publish/subscribe
- [02_multiple_subscribers.py](examples/02_multiple_subscribers.py) - Multiple subscribers
- [03_publisher_decorator.py](examples/03_publisher_decorator.py) - Publisher decorator
- [04_context_manager.py](examples/04_context_manager.py) - Context manager
- [05_statistics.py](examples/05_statistics.py) - Statistics functionality
- [06_rpc_pattern.py](examples/06_rpc_pattern.py) - RPC pattern
- [07_fastapi_integration.py](examples/07_fastapi_integration.py) - FastAPI integration

### EventBus Examples
- [08_eventbus_basic.py](examples/08_eventbus_basic.py) - EventBus basic usage
- [09_eventbus_decorator.py](examples/09_eventbus_decorator.py) - Decorator pattern
- [10_eventbus_scopes.py](examples/10_eventbus_scopes.py) - Event scopes
- [11_eventbus_context_manager.py](examples/11_eventbus_context_manager.py) - Context manager
- [12_eventbus_multiple_handlers.py](examples/12_eventbus_multiple_handlers.py) - Multiple handlers
- [13_eventbus_introspection.py](examples/13_eventbus_introspection.py) - Handler introspection
- [14_eventbus_custom_logger.py](examples/14_eventbus_custom_logger.py) - Custom logger
- [15_fastapi_eventbus_integration.py](examples/15_fastapi_eventbus_integration.py) - FastAPI complete integration

Running examples:

```bash
# AsyncQueueBroker examples
python examples/01_basic_pubsub.py

# EventBus examples
python examples/08_eventbus_basic.py

# FastAPI integration (requires Redis)
python examples/15_fastapi_eventbus_integration.py
```

## API Reference

### CloudEvent

```python
class CloudEvent(BaseModel):
    id: str                              # Auto-generated
    source: str                          # Required
    specversion: str = "1.0"            # Default value
    type: str                            # Required
    datacontenttype: Optional[str]       # Default "application/json"
    dataschema: Optional[str]
    subject: Optional[str]
    time: Optional[datetime]             # Auto-generated
    data: Optional[Dict[str, Any]]
    extensions: Dict[str, Any]           # Extension attributes

    def to_dict() -> Dict[str, Any]
    def to_json() -> str
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudEvent"
```

### SkyEvent

```python
class SkyEvent(CloudEvent):
    scope: EventScope = EventScope.APP   # Event scope

    @property
    def event_id(self) -> str            # Compatibility property
    @property
    def event_type(self) -> str          # Compatibility property
    @property
    def timestamp(self) -> datetime      # Compatibility property
```

### AsyncQueueBroker

```python
class AsyncQueueBroker:
    def __init__(self, url: str = "", *, max_queue_size: int = 1000)

    async def start() -> None
    async def stop() -> None
    async def connect() -> None
    async def ping(timeout: Optional[float] = None) -> bool

    def subscriber(self, channel: str, **kwargs) -> InMemorySubscriber
    def publisher(self, channel: str, **kwargs) -> InMemoryPublisher

    async def publish(
        self,
        message: Any = None,
        channel: Optional[str] = None,
        *,
        headers: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        reply_to: str = "",
        **kwargs
    ) -> int

    async def request(
        self,
        message: Any = None,
        channel: Optional[str] = None,
        *,
        timeout: float = 0.5,
        **kwargs
    ) -> Any

    def get_stats() -> Dict[str, Any]
    def get_subscribers() -> Dict[str, List[Dict[str, str]]]
```

### EventBus

```python
class EventBus:
    def __init__(
        self,
        process_level_broker: Any,
        app_level_broker: Any,
        logger: Optional[logging.Logger] = None
    )

    async def start() -> None
    async def stop() -> None

    def subscribe(self, event_type: str, handler: Callable) -> None
    async def publish(self, event: SkyEvent) -> None

    def get_handlers() -> Dict[str, List[Dict[str, str]]]

# Decorator
def event_handler(event_class: Type[SkyEvent]) -> Callable

# Initialization function
def init_eventbus(
    process_level_broker: Any,
    app_level_broker: Any,
    logger: Optional[logging.Logger] = None
) -> EventBus
```

## Best Practices

### 1. Choose Appropriate Event Scope

- **PROCESS Scope**: Suitable for scenarios without cross-instance communication
  - Cache updates
  - Local state changes
  - Fast-response internal events

- **APP Scope**: Suitable for scenarios requiring distributed processing
  - User registration/login
  - Order creation
  - Notification sending
  - Business requiring multi-instance coordination

### 2. Event Naming Convention

Use reverse domain name style:

```python
# Good naming
"com.example.user.created"
"com.example.order.payment.completed"
"com.example.notification.email.sent"

# Avoid
"user_created"
"ORDER_CREATED"
"notification"
```

### 3. Event Data Structure

Keep event data concise, include only necessary information:

```python
# Good practice
class UserCreatedEvent(SkyEvent):
    type: str = "user.created"
    user_id: str
    email: str
    created_at: datetime

# Avoid including large amounts of data in events
# If detailed information is needed, query in the handler
```

### 4. Error Handling

Exceptions in event handlers are caught and logged, won't affect other handlers:

```python
@event_handler(OrderCreatedEvent)
async def handle_order(event_data: dict):
    try:
        # Business logic
        await process_order(event_data)
    except Exception as e:
        logger.error(f"Failed to process order: {e}")
        # Can publish error event or perform compensation
```

### 5. Testing

Use AsyncQueueBroker for unit testing:

```python
import pytest
from eventbus.memory_broker import AsyncQueueBroker

@pytest.mark.asyncio
async def test_event_handling():
    broker = AsyncQueueBroker()
    received = []

    @broker.subscriber("test.event")
    async def handler(data: dict):
        received.append(data)

    await broker.start()
    await broker.publish({"value": 42}, channel="test.event")
    await asyncio.sleep(0.1)
    await broker.stop()

    assert len(received) == 1
    assert received[0]["value"] == 42
```

## FastStream Integration

EventBus can integrate with various FastStream brokers:

### Redis Broker

```python
from faststream.redis import RedisBroker

process_broker = AsyncQueueBroker()
app_broker = RedisBroker("redis://localhost:6379")
event_bus = EventBus(process_broker, app_broker)
```

### Kafka Broker

```python
from faststream.kafka import KafkaBroker

process_broker = AsyncQueueBroker()
app_broker = KafkaBroker("localhost:9092")
event_bus = EventBus(process_broker, app_broker)
```

### RabbitMQ Broker

```python
from faststream.rabbit import RabbitBroker

process_broker = AsyncQueueBroker()
app_broker = RabbitBroker("amqp://guest:guest@localhost:5672/")
event_bus = EventBus(process_broker, app_broker)
```

## Performance Considerations

- **AsyncQueueBroker**: Memory queue, highest performance, suitable for single process
- **In-process events (PROCESS)**: Direct invocation, lowest latency
- **Application-level events (APP)**: Distributed via broker, has network latency
- **Queue size**: Default 1000, adjustable via `max_queue_size`
- **Concurrent processing**: Each channel has independent consumer task

## Troubleshooting

### Events Not Being Processed

1. Check if broker is started: `await broker.start()`
2. Check if channel names match
3. Check if handler is correctly registered
4. Review log output

### RPC Timeout

1. Increase timeout parameter
2. Check if handler returns value
3. Confirm handler doesn't throw exceptions

### High Memory Usage

1. Reduce `max_queue_size`
2. Check for message backlog
3. Optimize handler performance

## License

Apache License 2.0

## Contributing

Issues and Pull Requests are welcome!

## Related Resources

- [CloudEvents Specification](https://github.com/cloudevents/spec)
- [FastStream Documentation](https://faststream.airt.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
