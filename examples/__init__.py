"""AsyncQueueBroker 使用示例

本目录包含 AsyncQueueBroker 的各种使用示例，演示如何使用兼容 FastStream API 的内存消息 Broker。

示例列表：
- 01_basic_pubsub.py: 基本发布/订阅
- 02_multiple_subscribers.py: 多订阅者
- 03_publisher_decorator.py: Publisher 装饰器
- 04_context_manager.py: 上下文管理器
- 05_eventbus_integration.py: EventBus 集成
- 06_statistics.py: 统计信息
- 07_rpc_pattern.py: RPC 请求-响应模式
- 08_fastapi_integration.py: FastAPI 集成

运行示例：
    python -m eventbus.examples.01_basic_pubsub
    python -m eventbus.examples.02_multiple_subscribers
    ...
"""
