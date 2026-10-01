"""Authentication and authorisation tables (docs/04 §1, docs/05 §2-4, docs/06).

Roles and permissions are **data**, not code: the catalogue in
:mod:`dentiva.domain.permissions` is seeded into ``permission`` at start-up and an
administrator can create custom roles that tick any subset.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.data.base import AuditColumns, Base


class Permission(Base):
    """One granular capability. ``is_financial`` drives the isolation tests."""

    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    group: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_financial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Role(AuditColumns, Base):
    """A named bundle of permissions. ``business_id`` NULL = system template."""

    __tablename__ = "role"
    __table_args__ = (Index("uq_role_business_id_name", "business_id", "name", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RolePermission(Base):
    """Membership of a permission in a role (composite primary key)."""

    __tablename__ = "role_permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permission.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (Index("uq_role_permission_pair", "role_id", "permission_id", unique=True),)


class User(AuditColumns, Base):
    """Login identity. ``is_system_admin`` is the bootstrap superuser flag."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_algo: Mapped[str] = mapped_column(String(40), nullable=False, default="argon2id")
    password_updated_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    session_timeout_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class UserRole(Base):
    """A user may hold several roles; effective permissions are the union."""

    __tablename__ = "user_role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (Index("uq_user_role_pair", "user_id", "role_id", unique=True),)


class SessionRecord(Base):
    """Login/logout/lock trail. Never holds credentials, only timestamps."""

    __tablename__ = "session_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    started_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    ended_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    host: Mapped[str | None] = mapped_column(String(120), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


class PasswordHistory(Base):
    """Last N password hashes, so a password cannot be reused immediately."""

    __tablename__ = "password_history"
    __table_args__ = (
        Index("ix_password_history_user_id_created_at_utc", "user_id", "created_at_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(nullable=False)
