"""基本发布/订阅示例

演示 AsyncQueueBroker 的基本用法，展示与 RedisBroker 相同的 API。
"""
import asyncio

from opensecflow.eventbus.memory_broker import AsyncQueueBroker


async def main():
    """基本的发布订阅，展示与 RedisBroker 相同的 API"""
    print("\n=== 基本发布/订阅示例 ===\n")

    # 替换 RedisBroker("redis://localhost:6379") 即可
    broker = AsyncQueueBroker()

    @broker.subscriber("events.order.created")
    async def handle_order(event_data: dict):
        print(f"  Received order event: {event_data}")

    await broker.start()
    await broker.publish(
        {"order_id": "ORD-001", "amount": 99.9},
        channel="events.order.created",
    )
    await asyncio.sleep(0.1)
    await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
