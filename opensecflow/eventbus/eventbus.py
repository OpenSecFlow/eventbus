import logging
import asyncio
from functools import wraps
from typing import Any, Dict, List, Callable, Type, Union, Optional
from opensecflow.eventbus.event import EventScope, ScopedEvent
from opensecflow.eventbus.memory_broker import AsyncQueueBroker


class EventBus:
    """Event Bus

    Supports dual-mode event handling:
    - In-process events: Directly calls local handlers, suitable for fast response;
    - Distributed events: Distributed via FastStream broker, suitable for cross-instance communication and broadcasting;
    """
    _process_level_broker: AsyncQueueBroker
    _app_level_broker: Any

    _handlers: Dict[str, List[Callable]]


    def __init__(self, process_level_broker: Any, app_level_broker: Any, logger: Optional[logging.Logger] = None):
        """Initialize EventBus

        :param process_level_broker: Broker instance for (local) in-process event handling
        :type process_level_broker: Any
        :param app_level_broker: Broker instance for (distributed) application-level event handling
        :type app_level_broker: Any
        :param logger: Logger instance, uses standard library logging if None
        :type logger: Optional[logging.Logger]
        """
        if process_level_broker is None:
            raise ValueError("process_level_broker can not be None")
        self._process_level_broker = process_level_broker
        if app_level_broker is None:
            raise ValueError("app_level_broker can not be None")
        self._app_level_broker = app_level_broker
        self._handlers = {}
        self._logger = logger if logger is not None else logging.getLogger(__name__)

    async def start(self):
        """Start EventBus and all brokers

        Starts process_level_broker and app_level_broker.
        """
        self._logger.info("Starting EventBus...")
        try:
            await self._process_level_broker.start()
            self._logger.info("Process level broker started")
        except Exception as e:
            self._logger.error(f"Failed to start process level broker: {e}")
            raise

        try:
            await self._app_level_broker.start()
            self._logger.info("App level broker started")
        except Exception as e:
            self._logger.error(f"Failed to start app level broker: {e}")
            # If app broker fails to start, stop the already started process broker
            await self._process_level_broker.stop()
            raise

        self._logger.info("EventBus started successfully")

    async def stop(self):
        """Stop EventBus and all brokers

        Stops process_level_broker and app_level_broker.
        """
        self._logger.info("Stopping EventBus...")
        errors = []

        try:
            await self._process_level_broker.stop()
            self._logger.info("Process level broker stopped")
        except Exception as e:
            self._logger.error(f"Failed to stop process level broker: {e}")
            errors.append(e)

        try:
            await self._app_level_broker.stop()
            self._logger.info("App level broker stopped")
        except Exception as e:
            self._logger.error(f"Failed to stop app level broker: {e}")
            errors.append(e)

        if errors:
            self._logger.error(f"EventBus stopped with {len(errors)} error(s)")
            raise Exception(f"Failed to stop some brokers: {errors}")
        else:
            self._logger.info("EventBus stopped successfully")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
        return False

    def subscribe(self, event_type: str, handler: Callable):
        """Register event handler

        Args:
            event_type: Event type
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

        # Construct channel name
        channel = f"events.{event_type}"

        # Register handler on both brokers
        self._process_level_broker.subscriber(channel)(handler)
        self._app_level_broker.subscriber(channel)(handler)

        self._logger.info(f"Registered handler '{handler.__name__}' for event '{event_type}'")

    async def publish(self, event: ScopedEvent):
        """Publish event

        Determines handling method based on event scope:
        - PROCESS: Directly calls local handlers
        - APP: Distributes via FastStream broker

        Args:
            event: Event instance
        """
        if event.scope == EventScope.PROCESS:
            # In-process handling
            await self._handle_local(event)
        else:
            # Distribute via FastStream broker
            await self._handle_distributed(event)

    def _get_channel(self, event: ScopedEvent) -> str:
        """Get channel name for the event

        Args:
            event: Event instance

        Returns:
            Channel name
        """
        return f"events.{event.event_type}"

    async def _handle_local(self, event: ScopedEvent):
        """Handle in-process event

        Handles in-process events via process_level_broker.

        Args:
            event: Event instance
        """
        channel = self._get_channel(event)
        # Get string value of scope (compatible with Enum and str)
        scope_value = event.scope.value if hasattr(event.scope, 'value') else event.scope
        self._logger.info(f"Processing {scope_value} event '{event.event_type}' via process broker")

        try:
            await self._process_level_broker.publish(
                event.to_dict(),
                channel=channel
            )
        except Exception as e:
            self._logger.error(f"Failed to publish event to process broker: {e}")

    async def _handle_distributed(self, event: ScopedEvent):
        """Handle distributed event via FastStream

        Publishes to broker channel, received by all workers.

        Args:
            event: Event instance
        """
        channel = self._get_channel(event)
        # Get string value of scope (compatible with Enum and str)
        scope_value = event.scope.value if hasattr(event.scope, 'value') else event.scope
        self._logger.info(f"Publishing {scope_value} event '{event.event_type}' to channel '{channel}'")

        try:
            await self._app_level_broker.publish(
                event.to_dict(),
                channel=channel
            )
        except Exception as e:
            self._logger.error(f"Failed to publish event: {e}")

    def get_handlers(self) -> Dict[str, List[Dict[str, str]]]:
        """Get all registered handlers

        Returns:
            Dictionary with event types as keys and handler info lists as values
        """
        result = {}
        for event_type, handlers in self._handlers.items():
            result[event_type] = [
                {
                    "function_name": handler.__name__,
                    "module": handler.__module__,
                }
                for handler in handlers
            ]
        return result


event_bus = None

# Pending handlers (collected before EventBus initialization)
_pending_handlers: List[tuple] = []


def event_handler(event_class: Type[ScopedEvent]):
    """Event handler function decorator

    Used to register event handlers to EventBus.
    Automatically converts dict payloads to Pydantic event instances.

    Args:
        event_class: ScopedEvent class

    Example:
        @event_handler(OrderCreatedEvent)
        async def handle_order(event: OrderCreatedEvent):
            # event is guaranteed to be OrderCreatedEvent instance, not dict
            pass
    """
    def decorator(func: Callable):
        # Extract event_type from ScopedEvent class
        if not (isinstance(event_class, type) and issubclass(event_class, ScopedEvent)):
            raise TypeError(f"event_handler expects ScopedEvent class, got {type(event_class)}")

        try:
            # Try to get type from class field default value (CloudEvent field name)
            if hasattr(event_class, 'model_fields') and 'type' in event_class.model_fields:
                field_info = event_class.model_fields['type']
                if hasattr(field_info, 'default') and field_info.default is not None:
                    event_type = field_info.default
                else:
                    raise ValueError(f"Event class {event_class.__name__} must have a default type")
            else:
                raise ValueError(f"Event class {event_class.__name__} must have a type field")
        except Exception as e:
            raise ValueError(f"Cannot extract event type from {event_class}: {e}")

        # Create a wrapper that automatically converts dict to Pydantic object
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Handle both positional and keyword arguments
            # FastStream may pass data as first positional arg or as keyword arg
            if args:
                data = args[0]
            elif kwargs:
                # Get the first keyword argument value (usually 'event', 'message', or 'data')
                data = next(iter(kwargs.values()))
            else:
                raise ValueError("No data provided to event handler")

            # Convert dict to Pydantic object if needed
            if isinstance(data, dict):
                data = event_class(**data)
            # Call the original handler
            return await func(data)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Handle both positional and keyword arguments
            if args:
                data = args[0]
            elif kwargs:
                # Get the first keyword argument value
                data = next(iter(kwargs.values()))
            else:
                raise ValueError("No data provided to event handler")

            # Convert dict to Pydantic object if needed
            if isinstance(data, dict):
                data = event_class(**data)
            # Call the original handler
            return func(data)

        # Choose appropriate wrapper based on whether func is async
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        # If EventBus is already initialized, register directly
        if event_bus is not None:
            event_bus.subscribe(event_type, wrapper)
        else:
            # Otherwise add to pending list
            _pending_handlers.append((event_type, wrapper))

        return wrapper
    return decorator


def init_eventbus(process_level_broker: Any, app_level_broker: Any,
                  logger: Optional[logging.Logger] = None) -> EventBus:
    """Initialize global EventBus instance

    Args:
        process_level_broker: Broker instance for in-process event handling
        app_level_broker: Broker instance for application-level event handling
        logger: Logger instance, uses standard library logging if None

    Returns:
        Initialized EventBus instance
    """
    global event_bus
    event_bus = EventBus(process_level_broker, app_level_broker, logger)

    # Register all pending handlers
    for event_type, handler in _pending_handlers:
        event_bus.subscribe(event_type, handler)

    event_bus._logger.info("EventBus initialized")
    return event_bus
