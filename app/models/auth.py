
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db.base import Base
from datetime import datetime

class UsedJTI(Base):
    __tablename__ = "used_jtis"
    jti = Column(String(36), primary_key=True)
    used_at = Column(DateTime, server_default=func.now())

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replaced_by_jti: Mapped[str | None] = mapped_column(String(36), ForeignKey("refresh_tokens.jti"), nullable=True)

class MfaState(Base):
    __tablename__ = "mfa_states"
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    last_step = Column(Integer, nullable=False, default=-1)

class ActionRateLimit(Base):
    __tablename__ = "action_rate_limits"

    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    action = Column(String(50), primary_key=True)
    last_attempt_at = Column(DateTime, nullable=False, default=func.now())
    attempt_count = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime, nullable=False, default=func.now())

class IpRateLimit(Base):
    __tablename__ = "ip_rate_limits"

    ip_address = Column(String(45), primary_key=True)
    action = Column(String(50), primary_key=True)
    last_attempt_at = Column(DateTime, nullable=False, default=func.now())
    attempt_count = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime, nullable=False, default=func.now())
