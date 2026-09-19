"""Platform-level identities for AutonomousIQ operators."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from libs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlatformUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Internal AutonomousIQ operator. Not attached to any customer tenant."""

    __tablename__ = "platform_users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
