"""RPC 请求-响应模式示例

演示 RPC（请求-响应）模式的使用。
"""
import asyncio

from eventbus.memory_broker import AsyncQueueBroker


async def main():
    """演示 RPC（请求-响应）模式"""
    print("\n=== RPC 请求-响应模式示例 ===\n")

    broker = AsyncQueueBroker()

    @broker.subscriber("calculator.add")
    async def add_service(data: dict) -> dict:
        result = data["a"] + data["b"]
        print(f"  [Service] Computing {data['a']} + {data['b']} = {result}")
        return {"result": result}

    @broker.subscriber("calculator.multiply")
    async def multiply_service(data: dict) -> dict:
        result = data["x"] * data["y"]
        print(f"  [Service] Computing {data['x']} * {data['y']} = {result}")
        return {"result": result}

    await broker.start()

    # 发送 RPC 请求并等待响应
    print("  [Client] Sending request: 5 + 3")
    response1 = await broker.request(
        {"a": 5, "b": 3},
        channel="calculator.add",
        timeout=1.0
    )
    print(f"  [Client] Got response: {response1['result']}\n")

    print("  [Client] Sending request: 7 * 6")
    response2 = await broker.request(
        {"x": 7, "y": 6},
        channel="calculator.multiply",
        timeout=1.0
    )
    print(f"  [Client] Got response: {response2['result']}\n")

    # 并发发送多个请求
    print("  [Client] Sending 3 concurrent requests...")
    tasks = [
        broker.request({"a": i, "b": i+1}, channel="calculator.add", timeout=1.0)
        for i in range(3)
    ]
    responses = await asyncio.gather(*tasks)
    print(f"  [Client] Got {len(responses)} responses: {[r['result'] for r in responses]}")

    await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
