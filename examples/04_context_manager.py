"""上下文管理器示例

演示使用 async with 自动管理 broker 生命周期。
"""
import asyncio

from eventbus.memory_broker import AsyncQueueBroker


async def main():
    """使用 async with 自动管理生命周期"""
    print("\n=== 上下文管理器示例 ===\n")

    async with AsyncQueueBroker() as broker:
        @broker.subscriber("chat")
        async def on_message(data):
            print(f"  Chat message: {data}")

        await broker.publish({"text": "Hello World"}, channel="chat")
        await asyncio.sleep(0.1)

    print("  Broker stopped automatically")


if __name__ == "__main__":
    asyncio.run(main())
