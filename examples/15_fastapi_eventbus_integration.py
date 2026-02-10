"""FastAPI with EventBus Integration

Demonstrates:
- Integrating EventBus with FastAPI application
- Publishing PROCESS scope events (in-memory, single instance)
- Publishing APP scope events (distributed via Redis)
- Using lifespan context manager for EventBus lifecycle
- RESTful API endpoints for event publishing

Requirements:
- Redis server running on localhost:6379
- Start Redis with: docker run -d -p 6379:6379 redis

API Endpoints:
- POST /events/process - Publish a PROCESS scope event
- POST /events/app - Publish an APP scope event
- GET /events/handlers - List all registered event handlers
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from eventbus.memory_broker import AsyncQueueBroker
from faststream.redis import RedisBroker
from eventbus.eventbus import EventBus, event_handler
from eventbus.event import SkyEvent, EventScope


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# Event Definitions
# ============================================================

class OrderCreatedEvent(SkyEvent):
    """Order created event - PROCESS scope"""
    type: str = "order.created"
    order_id: str
    customer_id: str
    amount: float
    scope: EventScope = EventScope.PROCESS


class NotificationEvent(SkyEvent):
    """Notification event - APP scope (distributed)"""
    type: str = "notification.sent"
    user_id: str
    message: str
    channel: str  # email, sms, push
    scope: EventScope = EventScope.APP


# ============================================================
# Request/Response Models
# ============================================================

class OrderCreateRequest(BaseModel):
    """Request model for creating an order"""
    order_id: str = Field(..., description="Unique order identifier")
    customer_id: str = Field(..., description="Customer identifier")
    amount: float = Field(..., gt=0, description="Order amount")


class NotificationRequest(BaseModel):
    """Request model for sending notification"""
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="Notification message")
    channel: str = Field(..., description="Notification channel (email/sms/push)")


class EventResponse(BaseModel):
    """Response model for event publishing"""
    success: bool
    event_id: str
    event_type: str
    scope: str
    message: str


# ============================================================
# Event Handlers
# ============================================================

@event_handler(OrderCreatedEvent)
async def handle_order_created(event_data: dict):
    """Handle order created event (PROCESS scope)"""
    logger.info(f"📦 Processing order: {event_data.get('order_id')} for customer {event_data.get('customer_id')}")
    # Simulate order processing
    await asyncio.sleep(0.1)
    logger.info(f"✅ Order {event_data.get('order_id')} processed successfully")


@event_handler(NotificationEvent)
async def handle_notification(event_data: dict):
    """Handle notification event (APP scope - distributed)"""
    logger.info(f"📧 Sending {event_data.get('channel')} notification to user {event_data.get('user_id')}")
    # Simulate notification sending
    await asyncio.sleep(0.1)
    logger.info(f"✅ Notification sent via {event_data.get('channel')}")


# ============================================================
# FastAPI Application with EventBus Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage EventBus lifecycle with FastAPI application"""
    logger.info("🚀 Starting FastAPI application with EventBus...")

    # Create brokers
    process_broker = AsyncQueueBroker()
    app_broker = RedisBroker("redis://localhost:6379")

    # Initialize EventBus
    from eventbus.eventbus import init_eventbus
    event_bus = init_eventbus(process_broker, app_broker)

    # Store in app state
    app.state.event_bus = event_bus

    try:
        # Start EventBus
        await event_bus.start()
        logger.info("✅ EventBus started successfully")

        yield

    except Exception as e:
        logger.error(f"❌ Failed to start EventBus: {e}")
        logger.info("💡 Make sure Redis is running: docker run -d -p 6379:6379 redis")
        raise
    finally:
        # Stop EventBus
        logger.info("🛑 Stopping EventBus...")
        try:
            await event_bus.stop()
            logger.info("✅ EventBus stopped successfully")
        except Exception as e:
            logger.error(f"⚠️ Error stopping EventBus: {e}")


# Create FastAPI app
app = FastAPI(
    title="EventBus FastAPI Integration",
    description="Demonstrates EventBus integration with FastAPI for PROCESS and APP scope events",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "EventBus FastAPI Integration",
        "endpoints": {
            "POST /events/process": "Publish PROCESS scope event (in-memory)",
            "POST /events/app": "Publish APP scope event (distributed via Redis)",
            "GET /events/handlers": "List all registered event handlers"
        },
        "docs": "/docs"
    }


@app.post("/events/process", response_model=EventResponse)
async def publish_process_event(request: OrderCreateRequest):
    """
    Publish a PROCESS scope event (in-memory, single instance only)

    PROCESS scope events are handled only within the current application instance.
    They use in-memory queue and are not distributed to other instances.
    """
    try:
        # Create event
        event = OrderCreatedEvent(
            source="order-service",
            order_id=request.order_id,
            customer_id=request.customer_id,
            amount=request.amount
        )

        # Publish event
        await app.state.event_bus.publish(event)

        return EventResponse(
            success=True,
            event_id=event.id,
            event_type=event.type,
            scope=event.scope.value,
            message=f"PROCESS event published: Order {request.order_id} created"
        )
    except Exception as e:
        logger.error(f"Failed to publish PROCESS event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events/app", response_model=EventResponse)
async def publish_app_event(request: NotificationRequest):
    """
    Publish an APP scope event (distributed via Redis)

    APP scope events are distributed to all application instances via Redis.
    All instances subscribed to this event will receive and process it.
    """
    try:
        # Create event
        event = NotificationEvent(
            source="notification-service",
            user_id=request.user_id,
            message=request.message,
            channel=request.channel
        )

        # Publish event
        await app.state.event_bus.publish(event)

        return EventResponse(
            success=True,
            event_id=event.id,
            event_type=event.type,
            scope=event.scope.value,
            message=f"APP event published: Notification sent to user {request.user_id}"
        )
    except Exception as e:
        logger.error(f"Failed to publish APP event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/handlers")
async def get_event_handlers():
    """
    Get all registered event handlers

    Returns information about all event handlers registered in the EventBus.
    """
    try:
        handlers = app.state.event_bus.get_handlers()

        # Format handler information
        formatted_handlers = {}
        for event_type, handler_list in handlers.items():
            formatted_handlers[event_type] = [
                {
                    "function": h["function_name"],
                    "module": h["module"]
                }
                for h in handler_list
            ]

        return {
            "total_event_types": len(handlers),
            "handlers": formatted_handlers
        }
    except Exception as e:
        logger.error(f"Failed to get handlers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Run Application
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*60)
    print("🚀 Starting FastAPI EventBus Integration Example")
    print("="*60)
    print("\n📋 Available endpoints:")
    print("  - POST http://localhost:8000/events/process")
    print("  - POST http://localhost:8000/events/app")
    print("  - GET  http://localhost:8000/events/handlers")
    print("\n📚 API Documentation:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("\n💡 Test with curl:")
    print('  curl -X POST "http://localhost:8000/events/process" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"order_id":"ORD-001","customer_id":"CUST-123","amount":99.99}\'')
    print()
    print('  curl -X POST "http://localhost:8000/events/app" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"user_id":"USER-001","message":"Hello!","channel":"email"}\'')
    print("\n" + "="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
