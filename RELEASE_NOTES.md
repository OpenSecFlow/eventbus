# Release Notes

## Version 0.2.0 (2026-02-12)

### 🚀 Type Safety Enhancement

Automatic dict-to-object conversion in event handlers for improved developer experience and type safety.

### ✨ Features

- **Automatic Type Conversion**: `@event_handler` decorator now automatically converts dict payloads to Pydantic event instances
- **Full Type Safety**: Handlers receive typed event objects with IDE autocomplete and validation
- **FastStream Compatibility**: Support for both positional and keyword arguments from different broker implementations
- **Backward Compatible**: Existing code works without changes

### 🧪 Testing

- Added comprehensive pytest test suite with 11 tests
- Test coverage: dict-to-object conversion, type safety, keyword argument handling
- Dev dependencies: `pytest>=7.0.0`, `pytest-asyncio>=0.21.0`

### 📚 Documentation

- Updated README.md and README_zh.md with type safety examples
- Enhanced CLAUDE.md with testing and handler registration guidance
- Added examples: `16_event_handler_auto_conversion.py`, `17_event_handler_type_safety.py`

### 🐛 Bug Fixes

- Fixed handler registration to properly register with brokers
- Fixed TypeError with FastStream brokers passing keyword arguments

### 🔄 Migration

No breaking changes. Optionally update handler type annotations for better type safety:

```python
# Recommended: Full type safety
@event_handler(OrderCreatedEvent)
async def handle_order(event: OrderCreatedEvent):
    print(f"Order {event.order_id}")
```

---

## Version 0.1.0 (2026-02-10)

### 🎉 Initial Release

First public release of opensecflow.eventbus - a Python event bus library based on the CloudEvents v1.0 specification.

### ✨ Features

#### Core Components

- **CloudEvent**: Full implementation of CloudEvents v1.0 specification
  - Required attributes: `id`, `source`, `specversion`, `type`
  - Optional attributes: `datacontenttype`, `dataschema`, `subject`, `time`, `data`
  - Extension attributes support
  - Validation for all required fields

- **ScopedEvent**: CloudEvent extension with scope functionality
  - `EventScope.PROCESS`: Process-level events (in-memory, single instance)
  - `EventScope.APP`: Application-level events (distributed across instances)
  - Backward compatibility properties: `event_id`, `event_type`, `timestamp`

- **EventBus**: Dual-broker event orchestrator
  - Routes events based on scope
  - Supports both in-process and distributed event handling
  - Async context manager support
  - Decorator-based handler registration via `@event_handler`
  - Handler introspection and management

- **AsyncQueueBroker**: FastStream-compatible in-memory broker
  - Subscriber/publisher decorators
  - RPC pattern support
  - Statistics tracking
  - Async lifecycle management

#### Integration

- **FastAPI Integration**: Full support with lifespan context managers
- **FastStream Compatibility**: Works with FastStream brokers (Redis, Kafka, etc.)
- **Pydantic v2**: Built on Pydantic v2 for robust data validation

### 📦 Package Structure

- **Namespace Package**: `opensecflow.eventbus`
- **Python Support**: Python 3.8+
- **Dependencies**:
  - `pydantic>=2.0.0`
  - `faststream>=0.5.0`

### 📚 Documentation

- Comprehensive CLAUDE.md for AI-assisted development
- 15 example files demonstrating various usage patterns
- Inline documentation in English

### 🔧 Development

- GitHub Actions CI/CD workflows
  - Build and test workflow
  - PyPI publishing workflow (manual and release-triggered)
- Apache 2.0 License

### 📝 Examples Included

1. **AsyncQueueBroker Examples** (01-07):
   - Basic pub/sub
   - Multiple subscribers
   - Publisher decorator
   - Context manager usage
   - Statistics tracking
   - RPC pattern
   - FastAPI integration

2. **EventBus Examples** (08-15):
   - Basic EventBus usage
   - Decorator pattern
   - Scope-based routing
   - Context manager
   - Multiple handlers
   - Introspection
   - Custom logger
   - FastAPI + EventBus integration

### 🔄 Migration Notes

This is the initial release. No migration needed.

### 🙏 Acknowledgments

Built with Claude Sonnet 4.5 assistance.

---

## Installation

```bash
pip install opensecflow.eventbus
```

## Quick Start

```python
from opensecflow.eventbus import EventBus, AsyncQueueBroker, ScopedEvent, EventScope

# Create brokers
process_broker = AsyncQueueBroker()
app_broker = AsyncQueueBroker()

# Initialize EventBus
bus = EventBus(process_broker, app_broker)

# Define event handler
@bus.event_handler
async def handle_event(event_data: dict):
    print(f"Received: {event_data}")

# Publish event
event = ScopedEvent(
    type="data.updated",
    source="my-service",
    data={"key": "value"},
    scope=EventScope.PROCESS
)

async with bus:
    await bus.publish(event)
```

## Links

- **Repository**: https://github.com/yourusername/eventbus
- **Documentation**: https://github.com/yourusername/eventbus#readme
- **PyPI**: https://pypi.org/project/opensecflow.eventbus/
- **License**: Apache 2.0
