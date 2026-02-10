"""统计信息示例

演示如何查看 broker 运行统计。
"""
import asyncio

from opensecflow.eventbus.memory_broker import AsyncQueueBroker


async def main():
    """查看 broker 运行统计"""
    print("\n=== 统计信息示例 ===\n")

    broker = AsyncQueueBroker()

    @broker.subscriber("metrics")
    async def handler(data):
        pass

    await broker.start()

    for i in range(5):
        await broker.publish({"value": i}, channel="metrics")

    await asyncio.sleep(0.2)
    stats = broker.get_stats()
    print(f"  Published: {stats['published']}")
    print(f"  Consumed:  {stats['consumed']}")
    print(f"  Errors:    {stats['errors']}")
    print(f"  Channels:  {stats['channels']}")
    print(f"  Running:   {stats['running']}")
    await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
