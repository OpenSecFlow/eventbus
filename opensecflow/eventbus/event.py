"""CloudEvent Specification Implementation

Event classes based on CloudEvents v1.0 specification
Specification: https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
import uuid


class EventScope(str, Enum):
    """Event Scope

    - PROCESS: Process-level events, handled only within the current instance
    - APP: Application-level events, distributed to all instances via FastStream
    """
    PROCESS = "process"
    APP = "app"


class CloudEvent(BaseModel):
    """CloudEvent Specification Event Class

    Implements core and extension attributes of CloudEvents v1.0 specification

    Required attributes:
        id: Unique event identifier
        source: Event source identifier (URI-reference)
        specversion: CloudEvents specification version
        type: Event type identifier

    Optional attributes:
        datacontenttype: Content type of data (e.g., application/json)
        dataschema: Schema identifier that data adheres to
        subject: Event subject, describes the specific object related to the event
        time: Timestamp when the event occurred
        data: Event payload data
    """

    # Required attributes
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier"
    )
    source: str = Field(
        ...,
        description="Event source identifier in URI-reference format"
    )
    specversion: str = Field(
        default="1.0",
        description="CloudEvents specification version"
    )
    type: str = Field(
        ...,
        description="Event type identifier, e.g., com.example.object.action"
    )

    # Optional attributes
    datacontenttype: Optional[str] = Field(
        default="application/json",
        description="Content type of data"
    )
    dataschema: Optional[str] = Field(
        default=None,
        description="Schema URI that data adheres to"
    )
    subject: Optional[str] = Field(
        default=None,
        description="Event subject, describes the specific object related to the event"
    )
    time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp (RFC3339 format)"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Event payload data"
    )

    # Extension attributes (can add any custom attributes)
    extensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="CloudEvents extension attributes"
    )

    @field_validator('specversion')
    @classmethod
    def validate_specversion(cls, v: str) -> str:
        """Validate specversion format"""
        if not v:
            raise ValueError("specversion cannot be empty")
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate type format"""
        if not v:
            raise ValueError("type cannot be empty")
        return v

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source format"""
        if not v:
            raise ValueError("source cannot be empty")
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
        """Convert to dictionary format

        Returns:
            Dictionary containing all non-null fields
        """
        result = self.model_dump(exclude_none=True, exclude={'extensions'})
        # Merge extension attributes to top level
        if self.extensions:
            result.update(self.extensions)
        return result

    def to_json(self) -> str:
        """Convert to JSON string

        Returns:
            Event data in JSON format
        """
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudEvent":
        """Create CloudEvent instance from dictionary

        Args:
            data: Dictionary containing event data

        Returns:
            CloudEvent instance
        """
        # Extract standard attributes
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
                # Other fields as extension attributes
                extensions[key] = value

        if extensions:
            event_data['extensions'] = extensions

        return cls(**event_data)


class ScopedEvent(CloudEvent):
    """Scoped Event Class

    CloudEvent-based event with scope functionality:
    - id: Unique event identifier (inherited from CloudEvent)
    - type: Event type (inherited from CloudEvent)
    - source: Event source (inherited from CloudEvent)
    - scope: Event scope (PROCESS/APP)
    - time: Event timestamp (inherited from CloudEvent)
    - data: Event data (inherited from CloudEvent)

    Control event distribution range via scope parameter:
    - EventScope.PROCESS: Handled only within the current process
    - EventScope.APP: Distributed to all application instances

    Example:
        # Create application-level event (default)
        event = ScopedEvent(
            type="data.updated",
            source="my-service",
            data={"key": "value"}
        )

        # Create process-level event
        event = ScopedEvent(
            type="cache.cleared",
            source="my-service",
            data={"cache_key": "user_123"},
            scope=EventScope.PROCESS
        )
    """
    scope: EventScope = Field(
        default=EventScope.APP,
        description="Event scope, defaults to application-level event"
    )

    # Backward compatibility convenience properties
    @property
    def event_id(self) -> str:
        """Get event ID (backward compatibility)"""
        return self.id

    @property
    def event_type(self) -> str:
        """Get event type (backward compatibility)"""
        return self.type

    @property
    def timestamp(self) -> datetime:
        """Get timestamp (backward compatibility)"""
        return self.time

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "data.updated",
                "source": "my-service",
                "scope": "app",
                "time": "2024-02-09T12:00:00Z",
                "data": {
                    "key": "value",
                    "user_id": "123"
                }
            }
        }
    )
