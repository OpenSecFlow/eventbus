"""多订阅者示例

演示多个 handler 订阅同一频道的场景。
"""
import asyncio

from opensecflow.eventbus.memory_broker import AsyncQueueBroker


async def main():
    """多个 handler 订阅同一频道"""
    print("\n=== 多订阅者示例 ===\n")

    broker = AsyncQueueBroker()

    @broker.subscriber("notifications")
    async def send_email(data: dict):
        print(f"  [Email] Sending to {data['email']}")

    @broker.subscriber("notifications")
    async def send_sms(data: dict):
        print(f"  [SMS] Sending to {data['phone']}")

    @broker.subscriber("notifications")
    async def log_notification(data: dict):
        print(f"  [Log] Notification: {data}")

    await broker.start()
    await broker.publish(
        {"email": "user@example.com", "phone": "138xxxx", "message": "Hello"},
        channel="notifications",
    )
    await asyncio.sleep(0.1)
    print(f"\n  Subscribers: {broker.get_subscribers()}")
    await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
