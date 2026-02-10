import logging
from typing import Any, Dict, List, Callable, Type, Union, Optional
from eventbus.event import EventScope, SkyEvent
from eventbus.memory_broker import AsyncQueueBroker


class EventBus:
    """事件总线

    支持双模式事件处理：
    - 进程内事件：直接调用本地 Handler, 适用于快速响应和;
    - 分布式事件：通过 FastStream broker 分发，适用于跨实例通信和广播;
    """
    _process_level_broker: AsyncQueueBroker
    _app_level_broker: Any

    _handlers: Dict[str, List[Callable]]


    def __init__(self, process_level_broker: Any, app_level_broker: Any, logger: Optional[logging.Logger] = None):
        """初始化 EventBus

        :param process_level_broker: (本地)进程内事件处理的 broker 实例
        :type process_level_broker: Any
        :param app_level_broker: (分布式)应用级别事件处理的 broker 实例
        :type app_level_broker: Any
        :param logger: 日志记录器，如果为 None 则使用标准库 logging
        :type logger: Optional[logging.Logger]
        """
        if process_level_broker is None:
            raise ValueError("process_level_broker can not be None")
        self._process_level_broker = process_level_broker
        if app_level_broker is None:
            raise ValueError("app_level_broker can not be None")
        self._app_level_broker = app_level_broker
        self._handlers = {}
        self._logger = logger if logger is not None else logging.getLogger(__name__)

    async def start(self):
        """启动 EventBus 和所有 broker

        启动 process_level_broker 和 app_level_broker。
        """
        self._logger.info("Starting EventBus...")
        try:
            await self._process_level_broker.start()
            self._logger.info("Process level broker started")
        except Exception as e:
            self._logger.error(f"Failed to start process level broker: {e}")
            raise

        try:
            await self._app_level_broker.start()
            self._logger.info("App level broker started")
        except Exception as e:
            self._logger.error(f"Failed to start app level broker: {e}")
            # 如果 app broker 启动失败，停止已启动的 process broker
            await self._process_level_broker.stop()
            raise

        self._logger.info("EventBus started successfully")

    async def stop(self):
        """停止 EventBus 和所有 broker

        停止 process_level_broker 和 app_level_broker。
        """
        self._logger.info("Stopping EventBus...")
        errors = []

        try:
            await self._process_level_broker.stop()
            self._logger.info("Process level broker stopped")
        except Exception as e:
            self._logger.error(f"Failed to stop process level broker: {e}")
            errors.append(e)

        try:
            await self._app_level_broker.stop()
            self._logger.info("App level broker stopped")
        except Exception as e:
            self._logger.error(f"Failed to stop app level broker: {e}")
            errors.append(e)

        if errors:
            self._logger.error(f"EventBus stopped with {len(errors)} error(s)")
            raise Exception(f"Failed to stop some brokers: {errors}")
        else:
            self._logger.info("EventBus stopped successfully")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.stop()
        return False

    def subscribe(self, event_type: str, handler: Callable):
        """注册事件 Handler

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

        # 构造 channel 名称
        channel = f"events.{event_type}"

        # 在两个 broker 上注册 handler
        self._process_level_broker.subscriber(channel)(handler)
        self._app_level_broker.subscriber(channel)(handler)

        self._logger.info(f"Registered handler '{handler.__name__}' for event '{event_type}'")

    async def publish(self, event: SkyEvent):
        """发布事件

        根据事件的 scope 决定处理方式：
        - PROCESS: 直接调用本地 Handler
        - APP: 通过 FastStream broker 分发

        Args:
            event: 事件实例
        """
        if event.scope == EventScope.PROCESS:
            # 进程内处理
            await self._handle_local(event)
        else:
            # 通过 FastStream broker 分发
            await self._handle_distributed(event)

    def _get_channel(self, event: SkyEvent) -> str:
        """获取事件的 channel 名称

        Args:
            event: 事件实例

        Returns:
            channel 名称
        """
        return f"events.{event.event_type}"

    async def _handle_local(self, event: SkyEvent):
        """处理进程内事件

        通过 process_level_broker 处理进程内事件。

        Args:
            event: 事件实例
        """
        channel = self._get_channel(event)
        # 获取 scope 的字符串值（兼容 Enum 和 str）
        scope_value = event.scope.value if hasattr(event.scope, 'value') else event.scope
        self._logger.info(f"Processing {scope_value} event '{event.event_type}' via process broker")

        try:
            await self._process_level_broker.publish(
                event.to_dict(),
                channel=channel
            )
        except Exception as e:
            self._logger.error(f"Failed to publish event to process broker: {e}")

    async def _handle_distributed(self, event: SkyEvent):
        """通过 FastStream 处理分布式事件

        发布到 broker channel，由所有 Worker 接收。

        Args:
            event: 事件实例
        """
        channel = self._get_channel(event)
        # 获取 scope 的字符串值（兼容 Enum 和 str）
        scope_value = event.scope.value if hasattr(event.scope, 'value') else event.scope
        self._logger.info(f"Publishing {scope_value} event '{event.event_type}' to channel '{channel}'")

        try:
            await self._app_level_broker.publish(
                event.to_dict(),
                channel=channel
            )
        except Exception as e:
            self._logger.error(f"Failed to publish event: {e}")

    def get_handlers(self) -> Dict[str, List[Dict[str, str]]]:
        """获取所有已注册的 Handlers

        Returns:
            字典，键为事件类型，值为 Handler 信息列表
        """
        result = {}
        for event_type, handlers in self._handlers.items():
            result[event_type] = [
                {
                    "function_name": handler.__name__,
                    "module": handler.__module__,
                }
                for handler in handlers
            ]
        return result


event_bus = None

# 待注册的 handlers（在 EventBus 初始化前收集）
_pending_handlers: List[tuple] = []


def event_handler(event_class: Type[SkyEvent]):
    """事件处理函数装饰器

    用于注册事件 Handler 到 EventBus。

    Args:
        event_class: SkyEvent 类

    Example:
        @event_handler(OrderCreatedEvent)
        async def handle_order(event: OrderCreatedEvent):
            pass
    """
    def decorator(func: Callable):
        # 从 SkyEvent 类中提取 event_type
        if not (isinstance(event_class, type) and issubclass(event_class, SkyEvent)):
            raise TypeError(f"event_handler expects SkyEvent class, got {type(event_class)}")

        try:
            # 尝试从类的字段默认值中获取 type（CloudEvent 的字段名）
            if hasattr(event_class, 'model_fields') and 'type' in event_class.model_fields:
                field_info = event_class.model_fields['type']
                if hasattr(field_info, 'default') and field_info.default is not None:
                    event_type = field_info.default
                else:
                    raise ValueError(f"Event class {event_class.__name__} must have a default type")
            else:
                raise ValueError(f"Event class {event_class.__name__} must have a type field")
        except Exception as e:
            raise ValueError(f"Cannot extract event type from {event_class}: {e}")

        # 如果 EventBus 已初始化，直接注册
        if event_bus is not None:
            if event_type not in event_bus._handlers:
                event_bus._handlers[event_type] = []
            event_bus._handlers[event_type].append(func)
            event_bus._logger.info(f"Registered handler '{func.__name__}' for event '{event_type}'")
        else:
            # 否则加入待注册列表
            _pending_handlers.append((event_type, func))

        return func
    return decorator


def init_eventbus(process_level_broker: Any, app_level_broker: Any,
                  logger: Optional[logging.Logger] = None) -> EventBus:
    """初始化全局 EventBus 实例

    Args:
        process_level_broker: 进程内事件处理的 broker 实例
        app_level_broker: 应用级别事件处理的 broker 实例
        logger: 日志记录器，如果为 None 则使用标准库 logging

    Returns:
        初始化后的 EventBus 实例
    """
    global event_bus
    event_bus = EventBus(process_level_broker, app_level_broker, logger)

    # 注册所有待处理的 handlers
    for event_type, handler in _pending_handlers:
        event_bus.subscribe(event_type, handler)

    event_bus._logger.info("EventBus initialized")
    return event_bus
