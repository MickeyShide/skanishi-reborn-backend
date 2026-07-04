import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CHAR, Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Index

from app.db.models.base import BaseSQLModel


class RefreshSession(BaseSQLModel, table=True):
    __tablename__ = "refresh_sessions"

    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_refresh_sessions_user_id_users",
            ),
            nullable=False,
        ),
    )

    jti: uuid.UUID = Field(sa_type=UUID(as_uuid=True), nullable=False)

    token_hash: str = Field(sa_type=CHAR(64), nullable=False)

    ip_address: str | None = Field(sa_type=String(45), nullable=True)
    user_agent: str | None = Field(default=None, nullable=True)

    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: datetime | None = Field(
        sa_type=DateTime(timezone=True), default=None, nullable=True
    )

    last_used_at: datetime | None = Field(
        sa_type=DateTime(timezone=True), default=None, nullable=True
    )

    replaced_by_session_id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "refresh_sessions.id",
                ondelete="SET NULL",
                name="fk_refresh_sessions_replaced_by_session_id_refresh_sessions",
            ),
            nullable=True,
        ),
    )

    __table_args__ = (
        Index("ix_refresh_sessions_user_id", "user_id"),
        Index("ux_refresh_sessions_jti", "jti", unique=True),
        Index("ux_refresh_sessions_token_hash", "token_hash", unique=True),
        Index("ix_refresh_sessions_expires_at", "expires_at"),
        Index(
            "ix_refresh_sessions_active",
            "id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )
