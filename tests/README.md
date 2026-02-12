# Tests for opensecflow.eventbus

This directory contains the test suite for the EventBus library, focusing on the automatic dict-to-object conversion feature in the `@event_handler` decorator.

## Test Files

### `test_event_handler_conversion.py`
Tests the automatic conversion of dict payloads to Pydantic event instances:
- Basic dict-to-object conversion
- Multiple events handling
- Type safety with various attribute types

### `test_event_handler_type_safety.py`
Tests type safety benefits of the enhanced decorator:
- OrderCreatedEvent type safety
- PaymentProcessedEvent type safety
- Multiple event types handling independently
- Direct attribute access without dict key checking

### `test_event_handler_kwargs.py`
Tests wrapper compatibility with both positional and keyword arguments:
- Positional argument handling (normal usage)
- Keyword argument handling (FastStream compatibility)
- Event object pass-through (backward compatibility)
- Ensures compatibility with FastStream brokers that may pass data as keyword arguments

## Running Tests

```bash
# Install dev dependencies first
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_event_handler_conversion.py -v
pytest tests/test_event_handler_kwargs.py -v

# Run specific test function
pytest tests/test_event_handler_conversion.py::test_event_handler_receives_typed_object -v
```

## Test Coverage

The test suite covers:
- ✅ Automatic dict-to-Pydantic conversion in event handlers
- ✅ Type safety for event attributes
- ✅ Multiple event types with different schemas
- ✅ Direct attribute access (no dict.get() needed)
- ✅ EventBus lifecycle management
- ✅ Backward compatibility with existing code
- ✅ FastStream broker compatibility (keyword argument support)

## Dependencies

- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
