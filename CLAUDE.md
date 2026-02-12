# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EventBus is a Python event bus library based on the CloudEvents v1.0 specification, supporting both in-process and distributed event handling. The library provides a dual-mode architecture for event processing with FastStream compatibility.

**Package Name**: `opensecflow.eventbus` (namespace package)

## Core Architecture

### Three-Layer Event System

1. **Event Layer** (`opensecflow/eventbus/event.py`)
   - `CloudEvent`: Base class implementing CloudEvents v1.0 specification
   - `ScopedEvent`: Extends CloudEvent with scope functionality
   - `EventScope`: Enum defining PROCESS (in-memory) vs APP (distributed) scopes

2. **Broker Layer** (`opensecflow/eventbus/memory_broker.py`)
   - `AsyncQueueBroker`: FastStream-compatible in-memory broker using asyncio.Queue
   - Provides subscriber/publisher decorators and RPC pattern support
   - Can be used standalone or as part of EventBus

3. **EventBus Layer** (`opensecflow/eventbus/eventbus.py`)
   - `EventBus`: Core orchestrator managing dual-broker architecture
   - Routes events based on scope: PROCESS events → process_broker, APP events → app_broker
   - Supports decorator-based handler registration via `@event_handler`

### Dual-Broker Pattern

EventBus requires TWO brokers at initialization:
- **process_level_broker**: Handles PROCESS scope events (fast, in-memory, single instance)
- **app_level_broker**: Handles APP scope events (distributed across instances via Redis/Kafka/etc)

Both can be `AsyncQueueBroker` for single-instance apps, or mix with FastStream brokers (RedisBroker, KafkaBroker) for distributed scenarios.

### Event Routing Logic

When `EventBus.publish(event)` is called:
- If `event.scope == EventScope.PROCESS`: Publishes to process_level_broker only
- If `event.scope == EventScope.APP`: Publishes to app_level_broker only
- Handlers are registered on BOTH brokers during `subscribe()`, but only the appropriate broker processes each event

## Development Commands

### Installation

```bash
# Install core dependencies (pydantic + faststream)
uv pip install -e .

# Install with FastAPI/uvicorn for examples
uv pip install -e ".[examples]"

# Install with Redis support for distributed events
uv pip install -e ".[redis]"

# Install with development dependencies (pytest, pytest-asyncio)
uv pip install -e ".[dev]"
```

### Running Examples

```bash
# Basic AsyncQueueBroker examples (no external dependencies)
python examples/01_basic_pubsub.py
python examples/08_eventbus_basic.py

# FastAPI integration (requires [examples] extra)
python examples/07_fastapi_integration.py

# Distributed examples (requires Redis and [redis] extra)
python examples/10_eventbus_scopes.py
python examples/15_fastapi_eventbus_integration.py

# Auto-conversion and type safety examples
python examples/16_event_handler_auto_conversion.py
python examples/17_event_handler_type_safety.py
```

### Testing

Test suite uses pytest with async support:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_event_handler_conversion.py -v
```

## Key Design Patterns

### Handler Registration

Two approaches:

1. **Direct subscription**:
```python
bus.subscribe("order.created", handler_function)
```

2. **Decorator pattern** (requires `init_eventbus()` first):
```python
@event_handler(OrderCreatedEvent)
async def handle_order(event: OrderCreatedEvent):
    # event is automatically converted to OrderCreatedEvent instance
    # Full type safety and IDE autocomplete available
    print(f"Order {event.order_id} with amount {event.amount}")
```

**Note**: The `@event_handler` decorator automatically converts dict payloads to Pydantic event instances, providing full type safety and IDE autocomplete support.

### Channel Naming Convention

Events are published to channels with format: `events.{event.type}`
- Event type "order.created" → channel "events.order.created"
- This is handled automatically by EventBus

### FastStream Compatibility

`AsyncQueueBroker` implements FastStream's broker interface:
- `subscriber(channel)` - decorator for handlers
- `publisher(channel)` - decorator for auto-publishing return values
- `publish(message, channel)` - manual publishing
- `request(message, channel, timeout)` - RPC pattern
- `start()` / `stop()` - lifecycle management

## Important Implementation Details

### Event Scope Behavior

- **PROCESS scope**: Events stay within the current process instance. Use for cache updates, local state changes, or when low latency is critical.
- **APP scope**: Events are distributed to all instances via the app_level_broker. Use for user actions, notifications, or cross-instance coordination.

### Broker Lifecycle

Both brokers must be started before publishing events:
```python
await bus.start()  # Starts both brokers
# ... publish events ...
await bus.stop()   # Stops both brokers
```

EventBus supports async context manager for automatic lifecycle:
```python
async with EventBus(process_broker, app_broker) as bus:
    # brokers auto-started
    await bus.publish(event)
    # brokers auto-stopped on exit
```

### Error Handling

- Handler exceptions are caught and logged but don't affect other handlers
- If app_level_broker fails to start, process_level_broker is automatically stopped
- `stop()` attempts to stop both brokers even if one fails, collecting all errors

## Dependencies

**Core** (always required):
- `pydantic>=2.0.0` - Event model validation
- `faststream>=0.5.0` - Broker interface compatibility

**Optional**:
- `fastapi>=0.100.0` + `uvicorn>=0.20.0` - For FastAPI integration examples
- `faststream[redis]>=0.5.0` - For Redis-based distributed events

## File Organization

```
opensecflow/
└── eventbus/
    ├── __init__.py          # Public API exports
    ├── event.py             # CloudEvent/ScopedEvent/EventScope
    ├── eventbus.py          # EventBus core + decorators
    └── memory_broker.py     # AsyncQueueBroker implementation

examples/
├── 01-07_*.py          # AsyncQueueBroker standalone examples
├── 08-15_*.py          # EventBus integration examples
└── 16-17_*.py          # Auto-conversion and type safety examples

tests/
├── test_event_handler_conversion.py  # Tests for dict-to-object conversion
└── test_event_handler_type_safety.py # Tests for type safety features
```

## Import Usage

```python
# Import from namespace package
from opensecflow.eventbus import EventBus, AsyncQueueBroker
from opensecflow.eventbus.event import ScopedEvent, EventScope
```

## Common Patterns

### FastAPI Integration

Use lifespan context manager to manage EventBus lifecycle:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    event_bus = init_eventbus(process_broker, app_broker)
    app.state.event_bus = event_bus
    await event_bus.start()
    yield
    await event_bus.stop()

app = FastAPI(lifespan=lifespan)
```

### Custom Event Classes

Inherit from `ScopedEvent` and set `type` and `scope`:

```python
class OrderCreatedEvent(ScopedEvent):
    type: str = "order.created"
    order_id: str
    amount: float
    scope: EventScope = EventScope.PROCESS  # or APP
```

The `source` parameter is required when creating event instances.

## License

Apache License 2.0
