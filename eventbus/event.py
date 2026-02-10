"""CloudEvent 规范实现

基于 CloudEvents v1.0 规范实现的事件类
规范文档: https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
import uuid


class EventScope(str, Enum):
    """事件作用域

    - PROCESS: 进程内事件，只在当前 FastAPI 实例处理
    - APP: 应用级事件，通过 FastStream 分发到所有实例
    """
    PROCESS = "process"
    APP = "app"


class CloudEvent(BaseModel):
    """CloudEvent 规范事件类

    实现 CloudEvents v1.0 规范的核心属性和扩展属性

    必需属性:
        id: 事件的唯一标识符
        source: 事件源的标识符（URI-reference）
        specversion: CloudEvents 规范版本
        type: 事件类型标识符

    可选属性:
        datacontenttype: data 的内容类型（如 application/json）
        dataschema: data 遵循的 schema 标识符
        subject: 事件主题，描述事件相关的具体对象
        time: 事件发生的时间戳
        data: 事件负载数据
    """

    # 必需属性
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="事件的唯一标识符"
    )
    source: str = Field(
        ...,
        description="事件源标识符，使用 URI-reference 格式"
    )
    specversion: str = Field(
        default="1.0",
        description="CloudEvents 规范版本"
    )
    type: str = Field(
        ...,
        description="事件类型标识符，如 com.example.object.action"
    )

    # 可选属性
    datacontenttype: Optional[str] = Field(
        default="application/json",
        description="data 的内容类型"
    )
    dataschema: Optional[str] = Field(
        default=None,
        description="data 遵循的 schema URI"
    )
    subject: Optional[str] = Field(
        default=None,
        description="事件主题，描述事件相关的具体对象"
    )
    time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="事件发生的时间戳（RFC3339 格式）"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="事件负载数据"
    )

    # 扩展属性（可以添加任意自定义属性）
    extensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="CloudEvents 扩展属性"
    )

    @field_validator('specversion')
    @classmethod
    def validate_specversion(cls, v: str) -> str:
        """验证 specversion 格式"""
        if not v:
            raise ValueError("specversion 不能为空")
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证 type 格式"""
        if not v:
            raise ValueError("type 不能为空")
        return v

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """验证 source 格式"""
        if not v:
            raise ValueError("source 不能为空")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "A234-1234-1234",
                "source": "/mycontext/subcontext",
                "specversion": "1.0",
                "type": "com.example.someevent",
                "datacontenttype": "application/json",
                "subject": "larger-context",
                "time": "2018-04-05T17:31:00Z",
                "data": {
                    "appinfoA": "abc",
                    "appinfoB": 123,
                    "appinfoC": True
                }
            }
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            包含所有非空字段的字典
        """
        result = self.model_dump(exclude_none=True, exclude={'extensions'})
        # 合并扩展属性到顶层
        if self.extensions:
            result.update(self.extensions)
        return result

    def to_json(self) -> str:
        """转换为 JSON 字符串

        Returns:
            JSON 格式的事件数据
        """
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudEvent":
        """从字典创建 CloudEvent 实例

        Args:
            data: 包含事件数据的字典

        Returns:
            CloudEvent 实例
        """
        # 提取标准属性
        standard_fields = {
            'id', 'source', 'specversion', 'type',
            'datacontenttype', 'dataschema', 'subject', 'time', 'data'
        }

        event_data = {}
        extensions = {}

        for key, value in data.items():
            if key in standard_fields:
                event_data[key] = value
            else:
                # 其他字段作为扩展属性
                extensions[key] = value

        if extensions:
            event_data['extensions'] = extensions

        return cls(**event_data)


class SkyEvent(CloudEvent):
    """Sky 事件类

    基于 CloudEvent 规范实现的 Sky 专用事件，包含事件作用域功能：
    - id: 唯一事件标识（继承自 CloudEvent）
    - type: 事件类型（继承自 CloudEvent）
    - source: 事件源（继承自 CloudEvent）
    - scope: 事件作用域 (PROCESS/APP)
    - time: 事件时间戳（继承自 CloudEvent）
    - data: 事件数据（继承自 CloudEvent）

    可以通过 scope 参数控制事件的分发范围：
    - EventScope.PROCESS: 仅在当前进程内处理
    - EventScope.APP: 分发到所有应用实例

    Example:
        # 创建应用级事件（默认）
        event = SkyEvent(
            type="sky.data.updated",
            source="sky-service",
            data={"key": "value"}
        )

        # 创建进程内事件
        event = SkyEvent(
            type="sky.cache.cleared",
            source="sky-service",
            data={"cache_key": "user_123"},
            scope=EventScope.PROCESS
        )
    """
    scope: EventScope = Field(
        default=EventScope.APP,
        description="事件作用域，默认为应用级事件"
    )

    # 为了向后兼容，添加便捷属性
    @property
    def event_id(self) -> str:
        """获取事件 ID（兼容旧接口）"""
        return self.id

    @property
    def event_type(self) -> str:
        """获取事件类型（兼容旧接口）"""
        return self.type

    @property
    def timestamp(self) -> datetime:
        """获取时间戳（兼容旧接口）"""
        return self.time

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "sky.data.updated",
                "source": "sky-service",
                "scope": "app",
                "time": "2024-02-09T12:00:00Z",
                "data": {
                    "key": "value",
                    "user_id": "123"
                }
            }
        }
    )

