"""Roles, permissions and their assignment to users (docs/05 §4).

The permission catalogue lives in :mod:`dentiva.domain.permissions` and is the
single source of truth; this service only persists which codes a role carries
and resolves the effective set for a user.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.errors import NotFound, ValidationError
from dentiva.data.models.security import Permission, Role, RolePermission, User, UserRole
from dentiva.data.seed.roles import ADMIN_ROLE, LOCKOUT_GUARD_PERMISSION, ROLE_TEMPLATES
from dentiva.domain.permissions import PERMISSIONS, spec_for
from dentiva.domain.rbac import can_remove_permission
from dentiva.services.rbac import internal, public_operation, require


@dataclass(frozen=True, slots=True)
class RoleSummary:
    """A role with the codes it grants, for the administration screen."""

    id: int
    name: str
    description: str
    is_system: bool
    is_active: bool
    codes: tuple[str, ...]
    member_count: int


@dataclass(frozen=True, slots=True)
class PermissionOption:
    """One entry of the permission catalogue, ready for a checklist."""

    code: str
    label: str
    group: str
    description: str
    sensitive: bool
    is_financial: bool


class RoleService:
    """Persist roles and resolve the effective permissions of a user."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("role.view", action="role.list", entity="role")
    def list_roles(self, db: DBSession, *, include_inactive: bool = False) -> list[RoleSummary]:
        """All roles with their permission codes and member counts."""
        statement = select(Role).order_by(Role.is_system.desc(), Role.name)
        if not include_inactive:
            statement = statement.where(Role.is_active.is_(True))
        roles = list(db.execute(statement).scalars().all())
        members = {
            row[0]: row[1]
            for row in db.execute(
                select(UserRole.role_id, func.count(UserRole.user_id)).group_by(UserRole.role_id)
            ).all()
        }
        return [self._summarise(db, role, members.get(role.id, 0)) for role in roles]

    @require("role.view", action="permission.catalogue", entity="permission")
    def permission_catalogue(self, db: DBSession) -> list[PermissionOption]:
        """The full catalogue, so the UI never invents a permission code."""
        return [
            PermissionOption(
                code=spec.code,
                label=spec.label,
                group=spec.group,
                description=spec.description,
                sensitive=spec.sensitive,
                is_financial=spec.is_financial,
            )
            for spec in PERMISSIONS
        ]

    @require("role.view", action="role.permissions.view", entity="user", entity_id_arg="user_id")
    def effective_permissions_for(self, db: DBSession, *, user_id: int) -> frozenset[str]:
        """The union of the permissions granted by all of a user's active roles."""
        return self.permissions_for(db, user_id)

    @require(
        "role.manage", action="role.permissions.update", entity="role", entity_id_arg="role_id"
    )
    def set_role_permissions(self, db: DBSession, *, role_id: int, codes: list[str]) -> RoleSummary:
        """Replace a role's permission set (sensitive: cannot drop the guard)."""
        role = db.get(Role, role_id)
        if role is None:
            raise NotFound("That role no longer exists.")
        unknown = [code for code in codes if spec_for(code) is None]
        if unknown:
            raise ValidationError(f"Unknown permission code(s): {', '.join(sorted(unknown))}.")
        if role.is_system and role.name == ADMIN_ROLE:
            # The Administrator role must keep every code; it is the only role
            # that can perform administration, so removing one would lock out
            # the whole product.
            missing = sorted({spec.code for spec in PERMISSIONS} - set(codes))
            if missing:
                raise ValidationError(
                    "The Administrator role must keep every permission. Missing: "
                    + ", ".join(missing)
                    + "."
                )
        self._replace_permissions(db, role, codes)
        return self._summarise(db, role, self._member_count(db, role.id))

    @require("role.manage", action="role.create", entity="role")
    def create_role(
        self, db: DBSession, *, name: str, description: str, codes: list[str]
    ) -> RoleSummary:
        """Create a role; names are unique (case-insensitive)."""
        clean = (name or "").strip()
        if not clean:
            raise ValidationError("Give the role a name.")
        exists = db.execute(
            select(Role).where(func.lower(Role.name) == func.lower(clean))
        ).scalar_one_or_none()
        if exists is not None:
            raise ValidationError(f"A role named '{clean}' already exists.")
        unknown = [code for code in codes if spec_for(code) is None]
        if unknown:
            raise ValidationError(f"Unknown permission code(s): {', '.join(sorted(unknown))}.")
        role = Role(name=clean, description=description.strip(), is_system=False, is_active=True)
        db.add(role)
        db.flush()
        self._replace_permissions(db, role, codes)
        return self._summarise(db, role, 0)

    @require("role.manage", action="role.update", entity="role", entity_id_arg="role_id")
    def rename_role(
        self, db: DBSession, *, role_id: int, name: str, description: str
    ) -> RoleSummary:
        """Rename or re-describe a role (system roles cannot be renamed)."""
        role = db.get(Role, role_id)
        if role is None:
            raise NotFound("That role no longer exists.")
        if role.is_system:
            raise ValidationError("Built-in roles cannot be renamed.")
        clean = (name or "").strip()
        if not clean:
            raise ValidationError("Give the role a name.")
        clash = db.execute(
            select(Role).where(
                func.lower(Role.name) == func.lower(clean),
                Role.id != role.id,
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise ValidationError(f"A role named '{clean}' already exists.")
        role.name = clean
        role.description = description.strip()
        db.flush()
        return self._summarise(db, role, self._member_count(db, role.id))

    @require("role.manage", action="role.deactivate", entity="role", entity_id_arg="role_id")
    def deactivate_role(self, db: DBSession, *, role_id: int) -> RoleSummary:
        """Deactivate a role; system roles are protected."""
        role = db.get(Role, role_id)
        if role is None:
            raise NotFound("That role no longer exists.")
        if role.is_system:
            raise ValidationError("Built-in roles cannot be deactivated.")
        role.is_active = False
        db.flush()
        return self._summarise(db, role, self._member_count(db, role.id))

    @require(
        "role.manage", action="role.permissions.update", entity="role", entity_id_arg="role_id"
    )
    def remove_permission(self, db: DBSession, *, role_id: int, code: str) -> RoleSummary:
        """Remove one permission, refusing the change that would lock out admins."""
        role = db.get(Role, role_id)
        if role is None:
            raise NotFound("That role no longer exists.")
        if not can_remove_permission(role.name, code, self._role_code_map(db)):
            raise ValidationError(
                "That permission cannot be removed: at least one role must keep "
                f"'{LOCKOUT_GUARD_PERMISSION}'."
            )
        current = set(self._codes_for(db, role.id))
        current.discard(code)
        self._replace_permissions(db, role, sorted(current))
        return self._summarise(db, role, self._member_count(db, role.id))

    @require("role.manage", action="role.assign", entity="user", entity_id_arg="user_id")
    def set_user_roles(
        self, db: DBSession, *, user_id: int, role_ids: list[int]
    ) -> tuple[str, ...]:
        """Replace the roles of a user (sensitive: can grant or revoke power)."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        chosen: list[Role] = []
        for role_id in dict.fromkeys(role_ids):
            role = db.get(Role, role_id)
            if role is None or not role.is_active:
                raise ValidationError("One of the selected roles no longer exists.")
            chosen.append(role)
        db.query(UserRole).filter(UserRole.user_id == user_id).delete(synchronize_session=False)
        for role in chosen:
            db.add(UserRole(user_id=user_id, role_id=role.id))
        db.flush()
        return tuple(role.name for role in chosen)

    # ------------------------------------------------------- internal helpers --
    @internal
    def role_names_for(self, db: DBSession, user_id: int) -> list[str]:
        """Internal: the active role names of a user."""
        return list(
            db.execute(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id, Role.is_active.is_(True))
                .order_by(Role.name)
            )
            .scalars()
            .all()
        )

    @internal
    def permissions_for(self, db: DBSession, user_id: int) -> frozenset[str]:
        """Internal: the union of the active permissions of a user."""
        codes = set(
            db.execute(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(
                    UserRole.user_id == user_id,
                    Role.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )
        if self._is_system_admin(db, user_id):
            codes |= {spec.code for spec in PERMISSIONS}
        return frozenset(codes)

    @internal
    def business_id_for(self, db: DBSession, user: User) -> int:
        """Internal: the business the user belongs to."""
        from dentiva.data.models.identity import Business

        business = db.execute(select(Business).order_by(Business.id)).scalars().first()
        return business.id if business else 0

    @public_operation
    def ensure_seeded(self, db: DBSession) -> None:
        """Bootstrap: create every permission and the built-in roles if absent.

        Called by the bootstrap service while the database is being prepared, so
        it cannot require a session — it is idempotent and safe to re-run.
        """
        by_code = {row.code: row for row in db.execute(select(Permission)).scalars().all()}
        for spec in PERMISSIONS:
            row = by_code.get(spec.code)
            if row is None:
                db.add(
                    Permission(
                        code=spec.code,
                        label=spec.label,
                        group=spec.group,
                        description=spec.description,
                        sensitive=spec.sensitive,
                        is_financial=spec.is_financial,
                    )
                )
        db.flush()
        by_code = {row.code: row for row in db.execute(select(Permission)).scalars().all()}
        existing = {row.name: row for row in db.execute(select(Role)).scalars().all()}
        for template in ROLE_TEMPLATES:
            role = existing.get(template.name)
            if role is None:
                role = Role(
                    name=template.name,
                    description=template.description,
                    is_system=True,
                    is_active=True,
                )
                db.add(role)
                db.flush()
                existing[template.name] = role
            if self._codes_for(db, role.id):
                continue
            codes = (
                sorted(template.codes)
                if template.name != ADMIN_ROLE
                else [s.code for s in PERMISSIONS]
            )
            for code in codes:
                permission = by_code.get(code)
                if permission is not None:
                    db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.flush()

    def _is_system_admin(self, db: DBSession, user_id: int) -> bool:
        value = db.execute(
            select(User.is_system_admin).where(User.id == user_id)
        ).scalar_one_or_none()
        return bool(value)

    def _role_code_map(self, db: DBSession) -> dict[str, frozenset[str]]:
        """Every role and the codes it currently grants (lock-out guard input)."""
        rows = db.execute(
            select(Role.id, Role.name, Permission.code)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
        ).all()
        mapping: dict[str, set[str]] = {row[1]: set() for row in rows}
        for _, name, code in rows:
            mapping[name].add(code)
        return {name: frozenset(codes) for name, codes in mapping.items()}

    def _codes_for(self, db: DBSession, role_id: int) -> list[str]:
        return list(
            db.execute(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role_id)
                .order_by(Permission.code)
            )
            .scalars()
            .all()
        )

    def _member_count(self, db: DBSession, role_id: int) -> int:
        return int(
            db.execute(
                select(func.count(UserRole.user_id)).where(UserRole.role_id == role_id)
            ).scalar_one()
        )

    def _replace_permissions(self, db: DBSession, role: Role, codes: list[str]) -> None:
        db.query(RolePermission).filter(RolePermission.role_id == role.id).delete(
            synchronize_session=False
        )
        wanted = {code for code in codes if spec_for(code) is not None}
        if wanted:
            ids = dict(
                db.execute(
                    select(Permission.code, Permission.id).where(Permission.code.in_(wanted))
                ).all()
            )
            for code in sorted(wanted):
                permission_id = ids.get(code)
                if permission_id is not None:
                    db.add(RolePermission(role_id=role.id, permission_id=permission_id))
        db.flush()

    def _summarise(self, db: DBSession, role: Role, member_count: int) -> RoleSummary:
        return RoleSummary(
            id=role.id,
            name=role.name,
            description=role.description or "",
            is_system=bool(role.is_system),
            is_active=bool(role.is_active),
            codes=tuple(self._codes_for(db, role.id)),
            member_count=member_count,
        )
