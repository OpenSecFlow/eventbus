"""Publisher 装饰器示例

演示使用 @broker.publisher 自动发布处理结果。
"""
import asyncio

from opensecflow.eventbus.memory_broker import AsyncQueueBroker


async def main():
    """使用 @broker.publisher 自动发布处理结果"""
    print("\n=== Publisher 装饰器示例 ===\n")

    broker = AsyncQueueBroker()

    @broker.subscriber("results")
    async def result_handler(data: dict):
        print(f"  Got result: {data}")

    @broker.subscriber("tasks")
    @broker.publisher("results")
    async def process_task(data: dict):
        print(f"  Processing task: {data}")
        return {"task_id": data["id"], "status": "done"}

    await broker.start()
    await broker.publish({"id": "T-001", "name": "build"}, channel="tasks")
    await asyncio.sleep(0.2)
    await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
