from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class ConstraintType(StrEnum):
    ALWAYS = "always"
    NEVER = "never"


class Base(DeclarativeBase):
    pass


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # uniq_participant_email_for_campaign
    __table_args__ = (
        UniqueConstraint("campaign_id", "email"),
        # names must be unique within a campaign
        UniqueConstraint("campaign_id", "name"),
    )


class Constraint(Base):
    __tablename__ = "constraints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    type: Mapped[ConstraintType] = mapped_column(String, nullable=False)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id"), nullable=False
    )
    giver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=False
    )
    receiver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("campaign_id", "type", "giver_id", "receiver_id"),
    )


class Pairing(Base):
    __tablename__ = "pairings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id"), nullable=False
    )
    giver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=False
    )
    receiver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participants.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    # can be set at the time when we generate the pairings
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # does not need to be set if the campaign is not email-based
    email_subject: Mapped[str | None] = mapped_column(String, nullable=True)

    is_pairings_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="f"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
