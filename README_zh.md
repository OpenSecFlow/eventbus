# EventBus

基于 CloudEvents 规范的 Python 事件总线库，支持进程内和分布式事件处理。

## 特性

- **CloudEvents 规范**: 完整实现 CloudEvents v1.0 规范
- **双模式事件处理**:
  - PROCESS 作用域：进程内快速事件处理
  - APP 作用域：跨实例分布式事件分发
- **FastStream 兼容**: 提供兼容 FastStream API 的内存 broker
- **RPC 支持**: 内置 request-response 模式
- **FastAPI 集成**: 无缝集成 FastAPI 应用
- **装饰器模式**: 简洁的事件处理器注册方式
- **统计和内省**: 内置事件统计和处理器查询功能

## 安装

```bash
# 使用 uv 安装（推荐）
uv pip install -e .

# 安装可选依赖（用于运行示例）
uv pip install -e ".[examples]"

# 安装 Redis 支持（用于分布式事件）
uv pip install -e ".[redis]"

# 安装开发依赖（pytest、pytest-asyncio）
uv pip install -e ".[dev]"

# 或仅安装核心依赖
pip install pydantic faststream
```

## 快速开始

### 基础用法

```python
import asyncio
from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from opensecflow.eventbus.eventbus import EventBus
from opensecflow.eventbus.event import ScopedEvent, EventScope

# 创建 brokers（为简单起见，两个都使用 AsyncQueueBroker）
process_broker = AsyncQueueBroker()
app_broker = AsyncQueueBroker()

# 创建 EventBus
bus = EventBus(process_broker, app_broker)

# 定义事件类
class OrderCreatedEvent(ScopedEvent):
    type: str = "order.created"
    order_id: str
    amount: float
    scope: EventScope = EventScope.PROCESS

# 定义处理函数
async def handle_order(event_data: dict):
    print(f"处理订单: {event_data['order_id']}")

# 订阅事件
bus.subscribe("order.created", handle_order)

# 启动 EventBus
await bus.start()

# 发布事件
event = OrderCreatedEvent(
    source="order-service",
    order_id="ORD-001",
    amount=99.9
)
await bus.publish(event)

# 停止 EventBus
await bus.stop()
```

### FastAPI 集成

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from opensecflow.eventbus.eventbus import init_eventbus, event_handler
from opensecflow.eventbus.event import ScopedEvent, EventScope

# 定义事件
class OrderCreatedEvent(ScopedEvent):
    type: str = "order.created"
    order_id: str
    scope: EventScope = EventScope.PROCESS

# 使用装饰器注册处理器，自动类型转换
@event_handler(OrderCreatedEvent)
async def handle_order(event: OrderCreatedEvent):
    # event 自动转换为 OrderCreatedEvent 实例
    # 完整的类型安全和 IDE 自动补全支持
    print(f"处理订单: {event.order_id}")

# FastAPI 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    process_broker = AsyncQueueBroker()
    app_broker = AsyncQueueBroker()
    event_bus = init_eventbus(process_broker, app_broker)
    app.state.event_bus = event_bus
    await event_bus.start()
    yield
    await event_bus.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/orders")
async def create_order(order_id: str, amount: float):
    event = OrderCreatedEvent(
        source="api",
        order_id=order_id,
        amount=amount
    )
    await app.state.event_bus.publish(event)
    return {"status": "created"}
```

### 分布式配置（可选）

如需跨多个实例的分布式事件处理，可使用 FastStream brokers：

```python
from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from faststream.redis import RedisBroker
from opensecflow.eventbus.eventbus import EventBus

# Process broker: 内存队列，用于快速的本地事件
process_broker = AsyncQueueBroker()

# App broker: Redis，用于跨实例的分布式事件
app_broker = RedisBroker("redis://localhost:6379")

bus = EventBus(process_broker, app_broker)
```

**注意**：Redis 支持需要安装 `[redis]` 额外依赖：`pip install -e ".[redis]"`。对于单实例应用，两个 broker 都可以使用 `AsyncQueueBroker`。

## 核心概念

### CloudEvent

基于 [CloudEvents v1.0 规范](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md) 实现的事件类。

**必需属性**:
- `id`: 事件唯一标识符（自动生成 UUID）
- `source`: 事件源标识符（URI-reference 格式）
- `specversion`: CloudEvents 规范版本（默认 "1.0"）
- `type`: 事件类型标识符

**可选属性**:
- `datacontenttype`: 数据内容类型（默认 "application/json"）
- `dataschema`: 数据 schema URI
- `subject`: 事件主题
- `time`: 事件时间戳（自动生成）
- `data`: 事件负载数据
- `extensions`: 扩展属性字典

### ScopedEvent

继承自 CloudEvent，添加了事件作用域功能。

**额外属性**:
- `scope`: 事件作用域（EventScope.PROCESS 或 EventScope.APP）

**EventScope 说明**:
- `PROCESS`: 进程内事件，仅在当前实例处理，使用内存队列，响应快速
- `APP`: 应用级事件，通过 broker（如 Redis）分发到所有实例

### AsyncQueueBroker

兼容 FastStream API 的内存 broker，适用于：
- 开发和测试环境
- 单进程应用
- 不需要 Redis 的场景

**主要方法**:
- `subscriber(channel)`: 创建订阅者装饰器
- `publisher(channel)`: 创建发布者装饰器
- `publish(message, channel)`: 发布消息
- `request(message, channel, timeout)`: RPC 请求
- `start()` / `stop()`: 启动/停止 broker
- `get_stats()`: 获取统计信息
- `get_subscribers()`: 获取订阅者信息

### EventBus

事件总线核心类，管理事件的订阅和发布。

**主要方法**:
- `subscribe(event_type, handler)`: 注册事件处理器
- `publish(event)`: 发布事件
- `start()` / `stop()`: 启动/停止事件总线
- `get_handlers()`: 获取所有注册的处理器

**装饰器**:
- `@event_handler(EventClass)`: 自动注册事件处理器

## 使用示例

### 1. 基础 Pub/Sub

```python
from eventbus.memory_broker import AsyncQueueBroker

broker = AsyncQueueBroker()

@broker.subscriber("events.user.created")
async def handle_user(data: dict):
    print(f"新用户: {data['username']}")

await broker.start()
await broker.publish({"username": "alice"}, channel="events.user.created")
await broker.stop()
```

### 2. 多个订阅者

```python
@broker.subscriber("events.order.created")
async def send_email(data: dict):
    print(f"发送邮件: 订单 {data['order_id']}")

@broker.subscriber("events.order.created")
async def update_inventory(data: dict):
    print(f"更新库存: 订单 {data['order_id']}")

await broker.publish({"order_id": "123"}, channel="events.order.created")
```

### 3. 发布者装饰器

```python
@broker.publisher("events.result")
async def process_data(data: dict) -> dict:
    # 返回值自动发布到 events.result
    return {"status": "processed", "data": data}

@broker.subscriber("events.result")
async def handle_result(data: dict):
    print(f"结果: {data}")

await process_data({"value": 42})
```

### 4. RPC 模式

```python
@broker.subscriber("rpc.calculate")
async def calculate(data: dict) -> dict:
    result = data["a"] + data["b"]
    return {"result": result}

# 发送请求并等待响应
response = await broker.request(
    {"a": 10, "b": 20},
    channel="rpc.calculate",
    timeout=1.0
)
print(response)  # {"result": 30}
```

### 5. 上下文管理器

```python
async with AsyncQueueBroker() as broker:
    @broker.subscriber("events.test")
    async def handler(data: dict):
        print(data)

    await broker.publish({"msg": "hello"}, channel="events.test")
    await asyncio.sleep(0.1)
```

### 6. 事件作用域

```python
# 进程内事件（快速）
process_event = ScopedEvent(
    type="cache.cleared",
    source="cache-service",
    scope=EventScope.PROCESS,
    data={"cache_key": "user_123"}
)
await bus.publish(process_event)

# 应用级事件（分布式）
app_event = ScopedEvent(
    type="user.registered",
    source="auth-service",
    scope=EventScope.APP,
    data={"user_id": "456"}
)
await bus.publish(app_event)
```

### 7. 统计信息

```python
stats = broker.get_stats()
print(f"已发布: {stats['published']}")
print(f"已消费: {stats['consumed']}")
print(f"错误数: {stats['errors']}")
print(f"通道数: {stats['channels']}")
print(f"订阅者: {stats['subscribers']}")
```

### 8. 处理器内省

```python
handlers = bus.get_handlers()
for event_type, handler_list in handlers.items():
    print(f"{event_type}:")
    for h in handler_list:
        print(f"  - {h['function_name']} ({h['module']})")
```

## 示例文件

[examples](examples/) 目录包含完整的示例代码：

### AsyncQueueBroker 示例
- [01_basic_pubsub.py](examples/01_basic_pubsub.py) - 基础发布订阅
- [02_multiple_subscribers.py](examples/02_multiple_subscribers.py) - 多订阅者
- [03_publisher_decorator.py](examples/03_publisher_decorator.py) - 发布者装饰器
- [04_context_manager.py](examples/04_context_manager.py) - 上下文管理器
- [05_statistics.py](examples/05_statistics.py) - 统计功能
- [06_rpc_pattern.py](examples/06_rpc_pattern.py) - RPC 模式
- [07_fastapi_integration.py](examples/07_fastapi_integration.py) - FastAPI 集成

### EventBus 示例
- [08_eventbus_basic.py](examples/08_eventbus_basic.py) - EventBus 基础用法
- [09_eventbus_decorator.py](examples/09_eventbus_decorator.py) - 装饰器模式
- [10_eventbus_scopes.py](examples/10_eventbus_scopes.py) - 事件作用域
- [11_eventbus_context_manager.py](examples/11_eventbus_context_manager.py) - 上下文管理器
- [12_eventbus_multiple_handlers.py](examples/12_eventbus_multiple_handlers.py) - 多处理器
- [13_eventbus_introspection.py](examples/13_eventbus_introspection.py) - 处理器内省
- [14_eventbus_custom_logger.py](examples/14_eventbus_custom_logger.py) - 自定义日志
- [15_fastapi_eventbus_integration.py](examples/15_fastapi_eventbus_integration.py) - FastAPI 完整集成

### 类型安全示例
- [16_event_handler_auto_conversion.py](examples/16_event_handler_auto_conversion.py) - 自动字典到对象转换
- [17_event_handler_type_safety.py](examples/17_event_handler_type_safety.py) - 类型安全演示

运行示例：

```bash
# AsyncQueueBroker 示例
python eventbus/examples/01_basic_pubsub.py

# EventBus 示例
python eventbus/examples/08_eventbus_basic.py

# FastAPI 集成（需要 Redis）
python eventbus/examples/15_fastapi_eventbus_integration.py
```

## API 参考

### CloudEvent

```python
class CloudEvent(BaseModel):
    id: str                              # 自动生成
    source: str                          # 必需
    specversion: str = "1.0"            # 默认值
    type: str                            # 必需
    datacontenttype: Optional[str]       # 默认 "application/json"
    dataschema: Optional[str]
    subject: Optional[str]
    time: Optional[datetime]             # 自动生成
    data: Optional[Dict[str, Any]]
    extensions: Dict[str, Any]           # 扩展属性

    def to_dict() -> Dict[str, Any]
    def to_json() -> str
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudEvent"
```

### ScopedEvent

```python
class ScopedEvent(CloudEvent):
    scope: EventScope = EventScope.APP   # 事件作用域

    @property
    def event_id(self) -> str            # 兼容属性
    @property
    def event_type(self) -> str          # 兼容属性
    @property
    def timestamp(self) -> datetime      # 兼容属性
```

### AsyncQueueBroker

```python
class AsyncQueueBroker:
    def __init__(self, url: str = "", *, max_queue_size: int = 1000)

    async def start() -> None
    async def stop() -> None
    async def connect() -> None
    async def ping(timeout: Optional[float] = None) -> bool

    def subscriber(self, channel: str, **kwargs) -> InMemorySubscriber
    def publisher(self, channel: str, **kwargs) -> InMemoryPublisher

    async def publish(
        self,
        message: Any = None,
        channel: Optional[str] = None,
        *,
        headers: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        reply_to: str = "",
        **kwargs
    ) -> int

    async def request(
        self,
        message: Any = None,
        channel: Optional[str] = None,
        *,
        timeout: float = 0.5,
        **kwargs
    ) -> Any

    def get_stats() -> Dict[str, Any]
    def get_subscribers() -> Dict[str, List[Dict[str, str]]]
```

### EventBus

```python
class EventBus:
    def __init__(
        self,
        process_level_broker: Any,
        app_level_broker: Any,
        logger: Optional[logging.Logger] = None
    )

    async def start() -> None
    async def stop() -> None

    def subscribe(self, event_type: str, handler: Callable) -> None
    async def publish(self, event: ScopedEvent) -> None

    def get_handlers() -> Dict[str, List[Dict[str, str]]]

# 装饰器（自动将字典转换为类型化的事件对象）
def event_handler(event_class: Type[ScopedEvent]) -> Callable

# 初始化函数
def init_eventbus(
    process_level_broker: Any,
    app_level_broker: Any,
    logger: Optional[logging.Logger] = None
) -> EventBus
```

## 最佳实践

### 1. 选择合适的事件作用域

- **PROCESS 作用域**：适用于不需要跨实例通信的场景
  - 缓存更新
  - 本地状态变更
  - 快速响应的内部事件

- **APP 作用域**：适用于需要分布式处理的场景
  - 用户注册/登录
  - 订单创建
  - 通知发送
  - 需要多实例协同的业务

### 2. 事件命名规范

使用反向域名风格：

```python
# 好的命名
"com.example.user.created"
"com.example.order.payment.completed"
"com.example.notification.email.sent"

# 避免
"user_created"
"ORDER_CREATED"
"notification"
```

### 3. 事件数据结构

保持事件数据简洁，只包含必要信息：

```python
# 好的实践
class UserCreatedEvent(ScopedEvent):
    type: str = "user.created"
    user_id: str
    email: str
    created_at: datetime

# 避免在事件中包含大量数据
# 如需详细信息，可在处理器中查询
```

### 4. 错误处理

事件处理器中的异常会被捕获并记录，不会影响其他处理器：

```python
@event_handler(OrderCreatedEvent)
async def handle_order(event_data: dict):
    try:
        # 业务逻辑
        await process_order(event_data)
    except Exception as e:
        logger.error(f"处理订单失败: {e}")
        # 可以发布错误事件或进行补偿操作
```

### 5. 测试

项目包含了完整的测试套件，使用 pytest 和异步支持：

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行所有测试
pytest tests/

# 详细输出模式
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_event_handler_conversion.py -v
```

使用 AsyncQueueBroker 进行单元测试的示例：

```python
import pytest
from opensecflow.eventbus.memory_broker import AsyncQueueBroker

@pytest.mark.asyncio
async def test_event_handling():
    broker = AsyncQueueBroker()
    received = []

    @broker.subscriber("test.event")
    async def handler(data: dict):
        received.append(data)

    await broker.start()
    await broker.publish({"value": 42}, channel="test.event")
    await asyncio.sleep(0.1)
    await broker.stop()

    assert len(received) == 1
    assert received[0]["value"] == 42
```

## 与 FastStream 集成

EventBus 可以与 FastStream 的各种 broker 集成：

### Redis Broker

```python
from faststream.redis import RedisBroker
from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from opensecflow.eventbus.eventbus import EventBus

process_broker = AsyncQueueBroker()
app_broker = RedisBroker("redis://localhost:6379")
event_bus = EventBus(process_broker, app_broker)
```

### Kafka Broker

```python
from faststream.kafka import KafkaBroker
from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from opensecflow.eventbus.eventbus import EventBus

process_broker = AsyncQueueBroker()
app_broker = KafkaBroker("localhost:9092")
event_bus = EventBus(process_broker, app_broker)
```

### RabbitMQ Broker

```python
from faststream.rabbit import RabbitBroker
from opensecflow.eventbus.memory_broker import AsyncQueueBroker
from opensecflow.eventbus.eventbus import EventBus

process_broker = AsyncQueueBroker()
app_broker = RabbitBroker("amqp://guest:guest@localhost:5672/")
event_bus = EventBus(process_broker, app_broker)
```

## 性能考虑

- **AsyncQueueBroker**: 内存队列，性能最高，适合单进程
- **进程内事件 (PROCESS)**: 直接调用，延迟最低
- **应用级事件 (APP)**: 通过 broker 分发，有网络延迟
- **队列大小**: 默认 1000，可通过 `max_queue_size` 调整
- **并发处理**: 每个 channel 有独立的消费者任务

## 故障排查

### 事件未被处理

1. 检查 broker 是否已启动：`await broker.start()`
2. 检查 channel 名称是否匹配
3. 检查处理器是否正确注册
4. 查看日志输出

### RPC 超时

1. 增加 timeout 参数
2. 检查处理器是否返回值
3. 确认处理器没有抛出异常

### 内存占用过高

1. 减小 `max_queue_size`
2. 检查是否有消息积压
3. 优化处理器性能

## 许可证

Apache License 2.0

## 贡献

欢迎提交 Issue 和 Pull Request！

## 相关资源

- [CloudEvents 规范](https://github.com/cloudevents/spec)
- [FastStream 文档](https://faststream.airt.ai/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
