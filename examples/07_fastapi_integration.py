"""FastAPI 集成示例

展示 FastAPI lifespan 集成方式。
"""

from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from eventbus.memory_broker import AsyncQueueBroker


broker = AsyncQueueBroker()

@broker.subscriber("events.order.created")
async def on_order_created(event_data: dict):
    print(f"Order created: {event_data}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.start()
    yield
    await broker.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/orders")
async def create_order(order: dict):
    await broker.publish(order, channel="events.order.created")
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
