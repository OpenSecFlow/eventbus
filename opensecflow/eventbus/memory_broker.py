"""FastStream-compatible in-memory broker

A drop-in replacement for FastStream's RedisBroker that uses asyncio.Queue
for in-process message passing. Designed for development, testing, and
single-process scenarios where Redis is not available or not desired.

Usage:
    from eventbus.memory_broker import AsyncQueueBroker

    # Replace: broker = RedisBroker("redis://localhost:6379")
    # With:
    broker = AsyncQueueBroker()

    @broker.subscriber("events.order.created")
    async def handle_order(event_data: dict):
        print(f"Received: {event_data}")

    await broker.start()
    await broker.publish({"order_id": "123"}, channel="events.order.created")
    await broker.stop()
"""
import asyncio
import functools
import uuid
from typing import Any, Callable, Dict, List, Optional


class InMemorySubscriber:
    """Subscriber object returned by broker.subscriber().

    Acts as a decorator: when applied to a function, registers that function
    as the handler for the subscriber's channel.
    """

    def __init__(self, channel: str, broker: "AsyncQueueBroker") -> None:
        self.channel = channel
        self._broker = broker
        self._handler: Optional[Callable] = None
        self._handler_name: str = ""

    def __call__(self, func: Callable) -> Callable:
        """Register the decorated function as this subscriber's handler."""
        self._handler = func
        self._handler_name = getattr(func, "__name__", repr(func))
        self._broker._register_subscriber(self.channel, self)
        return func


class InMemoryPublisher:
    """Publisher object returned by broker.publisher().

    Acts as a decorator: wraps a function so that its return value is
    automatically published to the publisher's channel.
    """

    def __init__(self, channel: str, broker: "AsyncQueueBroker") -> None:
        self.channel = channel
        self._broker = broker

    def __call__(self, func: Callable) -> Callable:
        """Wrap the decorated function to auto-publish its return value."""
        broker = self._broker
        channel = self.channel

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            if result is not None:
                await broker.publish(result, channel=channel)
            return result

        return wrapper


class AsyncQueueBroker:
    """In-memory broker with FastStream-compatible API.

    Drop-in replacement for RedisBroker in single-process scenarios.
    Uses asyncio.Queue internally for async message delivery.

    Args:
        url: Accepted for API compatibility with RedisBroker, ignored.
        max_queue_size: Maximum size of per-channel message queues.
    """

    def __init__(self, url: str = "", *, max_queue_size: int = 1000) -> None:
        self._url = url  # accepted but ignored
        self._max_queue_size = max_queue_size
        self._subscribers: Dict[str, List[InMemorySubscriber]] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._consumer_tasks: List[asyncio.Task] = []
        self._running = False
        self._stats = {
            "published": 0,
            "consumed": 0,
            "errors": 0,
        }
        # For request-response pattern
        self._pending_requests: Dict[str, asyncio.Future] = {}

    # --- Lifecycle ---

    async def start(self) -> None:
        """Start the broker and launch consumer tasks for registered channels."""
        if self._running:
            return
        self._running = True
        for channel in self._subscribers:
            self._ensure_consumer(channel)

    async def stop(self, *args: Any, **kwargs: Any) -> None:
        """Stop the broker and cancel all consumer tasks."""
        if not self._running:
            return
        self._running = False
        for task in self._consumer_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._consumer_tasks.clear()

    async def connect(self) -> None:
        """Connect to the broker (alias for start, API compatibility)."""
        await self.start()

    async def ping(self, timeout: Optional[float] = None) -> bool:
        """Check if the broker is alive. Always returns True."""
        return True

    async def __aenter__(self) -> "AsyncQueueBroker":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    # --- Registration ---

    def subscriber(
        self,
        channel: str,
        **kwargs: Any,
    ) -> InMemorySubscriber:
        """Create a subscriber decorator for a channel.

        Usage::

            @broker.subscriber("events.order.created")
            async def handle(data: dict):
                ...

        Args:
            channel: Channel name to subscribe to.
            **kwargs: Accepted for API compatibility, ignored.

        Returns:
            An InMemorySubscriber that acts as a decorator.
        """
        return InMemorySubscriber(channel=channel, broker=self)

    def publisher(
        self,
        channel: str,
        **kwargs: Any,
    ) -> InMemoryPublisher:
        """Create a publisher decorator for a channel.

        Usage::

            @broker.publisher("response-channel")
            async def process(data: dict) -> dict:
                return {"status": "ok"}

        Args:
            channel: Channel name to publish return values to.
            **kwargs: Accepted for API compatibility, ignored.

        Returns:
            An InMemoryPublisher that acts as a decorator.
        """
        return InMemoryPublisher(channel=channel, broker=self)

    # --- Publishing ---

    async def publish(
        self,
        message: Any = None,
        channel: Optional[str] = None,
        *,
        headers: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        reply_to: str = "",
        **kwargs: Any,
    ) -> int:
        """Publish a message to a channel.

        Matches the RedisBroker.publish() signature for the parameters
        actually used in this project.

        Args:
            message: The message payload.
            channel: Target channel name.
            headers: Message headers (accepted, stored but not used).
            correlation_id: Correlation ID (accepted, ignored).
            reply_to: Reply-to channel (accepted, ignored).
            **kwargs: Additional kwargs for API compatibility.

        Returns:
            Number of subscribers that will receive the message.

        Raises:
            RuntimeError: If the broker has not been started.
            ValueError: If channel is not specified.
        """
        if not self._running:
            raise RuntimeError("Broker is not running. Call await broker.start() first.")
        if channel is None:
            raise ValueError("channel is required")

        subscribers = self._subscribers.get(channel, [])
        if not subscribers:
            return 0

        self._ensure_consumer(channel)
        queue = self._queues[channel]

        # Wrap message with metadata for RPC support
        message_envelope = {
            "_payload": message,
            "_headers": headers or {},
        }

        try:
            queue.put_nowait(message_envelope)
        except asyncio.QueueFull:
            self._stats["errors"] += 1
            return 0

        self._stats["published"] += 1
        return len(subscribers)

    async def request(
        self,
        message: Any = None,
        channel: Optional[str] = None,
        *,
        timeout: float = 0.5,
        **kwargs: Any,
    ) -> Any:
        """Send a request and wait for a response (RPC pattern).

        Publishes a message with a unique correlation ID and waits for a
        response on a temporary reply channel.

        Args:
            message: The request payload.
            channel: Target channel name.
            timeout: Maximum time to wait for response in seconds.
            **kwargs: Additional kwargs for API compatibility.

        Returns:
            The response message from the handler.

        Raises:
            RuntimeError: If the broker has not been started.
            ValueError: If channel is not specified.
            asyncio.TimeoutError: If no response received within timeout.
        """
        if not self._running:
            raise RuntimeError("Broker is not running. Call await broker.start() first.")
        if channel is None:
            raise ValueError("channel is required")

        # Generate unique correlation ID
        correlation_id = str(uuid.uuid4())

        # Create a future to wait for the response
        response_future: asyncio.Future = asyncio.Future()
        self._pending_requests[correlation_id] = response_future

        # Create temporary reply channel
        reply_channel = f"_reply.{correlation_id}"

        # Register temporary subscriber for the reply
        reply_sub = self.subscriber(reply_channel)

        async def _reply_handler(response: Any) -> None:
            if correlation_id in self._pending_requests:
                future = self._pending_requests.pop(correlation_id)
                if not future.done():
                    future.set_result(response)

        # Apply the decorator
        reply_sub(_reply_handler)

        try:
            # Publish the request with reply_to metadata
            await self.publish(
                message,
                channel=channel,
                headers={"reply_to": reply_channel, "correlation_id": correlation_id},
            )

            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            # Clean up on timeout
            self._pending_requests.pop(correlation_id, None)
            raise

    # --- Internal ---

    def _register_subscriber(self, channel: str, sub: InMemorySubscriber) -> None:
        """Register a subscriber for a channel (called by InMemorySubscriber)."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(sub)

        if self._running:
            self._ensure_consumer(channel)

    def _ensure_consumer(self, channel: str) -> None:
        """Ensure a queue and consumer task exist for the given channel."""
        if channel not in self._queues:
            self._queues[channel] = asyncio.Queue(maxsize=self._max_queue_size)
            task = asyncio.create_task(self._consumer_loop(channel))
            self._consumer_tasks.append(task)

    async def _consumer_loop(self, channel: str) -> None:
        """Background task that consumes messages from a channel's queue."""
        queue = self._queues[channel]
        while self._running:
            try:
                message_envelope = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            # Extract message and metadata
            if isinstance(message_envelope, dict) and "_payload" in message_envelope:
                message = message_envelope["_payload"]
                headers = message_envelope.get("_headers", {})
            else:
                # Backward compatibility: treat as plain message
                message = message_envelope
                headers = {}

            handlers = self._subscribers.get(channel, [])
            for sub in handlers:
                if sub._handler is not None:
                    try:
                        # Call the handler
                        if asyncio.iscoroutinefunction(sub._handler):
                            result = await sub._handler(message)
                        else:
                            result = sub._handler(message)

                        self._stats["consumed"] += 1

                        # If this is an RPC request, send the response
                        reply_to = headers.get("reply_to")
                        if reply_to and result is not None:
                            await self.publish(result, channel=reply_to)

                    except Exception as e:
                        self._stats["errors"] += 1
                        print(
                            f"Error in handler '{sub._handler_name}' "
                            f"for channel '{channel}': {e}"
                        )

            queue.task_done()

    # --- Diagnostics ---

    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics."""
        return {
            **self._stats,
            "running": self._running,
            "channels": len(self._subscribers),
            "subscribers": sum(len(subs) for subs in self._subscribers.values()),
            "queue_sizes": {
                ch: self._queues[ch].qsize()
                for ch in self._queues
            },
        }

    def get_subscribers(self) -> Dict[str, List[Dict[str, str]]]:
        """Get information about all registered subscribers."""
        return {
            channel: [
                {
                    "handler": sub._handler_name,
                    "channel": sub.channel,
                }
                for sub in subs
            ]
            for channel, subs in self._subscribers.items()
        }
