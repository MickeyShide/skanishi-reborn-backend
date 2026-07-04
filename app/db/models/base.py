from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger, Identity, String, func
from sqlmodel import Field, SQLModel


class BaseSQLModel(SQLModel):
    __abstract__ = True

    id: int | None = Field(
        sa_type=BigInteger,
        default=None,
        primary_key=True,
        sa_column_args=(Identity(),),
    )

    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )

    updated_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        nullable=False,
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.current_timestamp(),
        },
    )


class SlugSQLModel(SQLModel):
    __abstract__ = True

    id: str = Field(sa_type=String(96), primary_key=True, nullable=False)

    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )

    updated_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        nullable=False,
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.current_timestamp(),
        },
    )
