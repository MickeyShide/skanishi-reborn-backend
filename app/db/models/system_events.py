from enum import StrEnum
from typing import Any

from sqlalchemy import Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Column

from app.db.models.base import BaseSQLModel


class OutboxEventStatus(StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"


class OutboxEvent(BaseSQLModel, table=True):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_outbox_events_status", "status"),
    )

    event_type: str = Field(nullable=False)
    payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    status: OutboxEventStatus = Field(
        sa_type=SAEnum(OutboxEventStatus, name="outboxeventstatus"),
        default=OutboxEventStatus.PENDING,
        nullable=False,
    )


class ProcessedEvent(BaseSQLModel, table=True):
    __tablename__ = "processed_events"

    event_id: str = Field(nullable=False, unique=True, index=True)
    status: str = Field(nullable=False, default="DONE")
