"""Typed settings store (docs/05 §7, REQ-SET-010…014).

Every setting is declared in :mod:`dentiva.core.config`; this service reads and
writes the ``settings`` table, validating each value against its declaration so
a corrupt row can never reach the UI. Changes are audited because they can alter
security behaviour (auto-lock) or where clinic data is written (backups).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import utc_now
from dentiva.core.config import (
    NS_BACKUP,
    SETTING_SPECS,
    AppConfig,
    SettingSpec,
    spec_for,
)
from dentiva.core.errors import ValidationError
from dentiva.data.models.ops import Setting
from dentiva.security.session import current
from dentiva.services.rbac import internal, public_operation, require


@dataclass(frozen=True, slots=True)
class SettingValue:
    """One setting with its resolved value and declaration."""

    namespace: str
    key: str
    value: Any
    spec: SettingSpec

    @property
    def label(self) -> str:
        return self.spec.label

    @property
    def is_default(self) -> bool:
        return self.value == self.spec.default


class SettingsService:
    """Read and write the configuration store."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    @require("settings.view", action="settings.list", entity="setting")
    def all(self, db: DBSession) -> list[SettingValue]:
        """Every declared setting with its current (or default) value."""
        stored = {
            (row.namespace, row.key): _decode(row.value_json, row.value_type)
            for row in db.execute(select(Setting)).scalars().all()
        }
        values: list[SettingValue] = []
        for spec in SETTING_SPECS:
            value = stored.get(spec.path, spec.default)
            values.append(
                SettingValue(
                    namespace=spec.namespace,
                    key=spec.key,
                    value=value,
                    spec=spec,
                )
            )
        return values

    @require("settings.view", action="settings.snapshot", entity="setting")
    def snapshot(self, db: DBSession) -> AppConfig:
        """A resolved copy of the whole configuration (cheap to hold in memory)."""
        return self._snapshot(db)

    @public_operation
    def public_snapshot(self, db: DBSession) -> AppConfig:
        """Public bootstrap: the configuration before anyone is signed in."""
        return self._snapshot(db)

    def _snapshot(self, db: DBSession) -> AppConfig:
        stored = {
            (row.namespace, row.key): _decode(row.value_json, row.value_type)
            for row in db.execute(select(Setting)).scalars().all()
        }
        resolved: dict[tuple[str, str], Any] = {}
        for spec in SETTING_SPECS:
            value = stored.get(spec.path, spec.default)
            resolved[spec.path] = value if _is_valid(spec, value) else spec.default
        return AppConfig(values=resolved)

    @require("settings.view", action="settings.get", entity="setting")
    def value(self, db: DBSession, *, namespace: str, key: str) -> Any:
        """One value, or the declared default when it has never been set."""
        spec = spec_for(namespace, key)
        row = self._row(db, namespace, key)
        if row is None:
            return spec.default
        decoded = _decode(row.value_json, row.value_type)
        return decoded if _is_valid(spec, decoded) else spec.default

    @require("settings.manage", action="settings.update", entity="setting")
    def update(self, db: DBSession, *, namespace: str, key: str, value: Any) -> SettingValue:
        """Validate and store one setting (sensitive: audited change)."""
        return self._update(db, namespace=namespace, key=key, value=value)

    @internal
    def _update(self, db: DBSession, *, namespace: str, key: str, value: Any) -> SettingValue:
        spec = spec_for(namespace, key)
        try:
            clean = spec.validate(value)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        row = self._row(db, namespace, key)
        if row is None:
            row = Setting(
                namespace=namespace,
                key=key,
                value_json="",
                value_type=_kind_of(clean),
                is_sensitive=spec.sensitive,
                updated_at_utc=utc_now(),
            )
            db.add(row)
        row.value_json = json.dumps(clean, ensure_ascii=False)
        row.value_type = _kind_of(clean)
        row.is_sensitive = spec.sensitive
        row.updated_by_user_id = _current_user_id()
        row.updated_at_utc = utc_now()
        db.flush()
        return SettingValue(namespace=namespace, key=key, value=clean, spec=spec)

    @require("settings.manage", action="settings.update_many", entity="setting")
    def update_many(self, db: DBSession, *, changes: dict[tuple[str, str], Any]) -> AppConfig:
        """Apply several settings in one audited transaction."""
        for (namespace, key), value in changes.items():
            self._update(db, namespace=namespace, key=key, value=value)
        return self.snapshot(db)

    @require("settings.manage", action="settings.reset", entity="setting")
    def reset(self, db: DBSession, *, namespace: str, key: str) -> SettingValue:
        """Restore a setting to its declared default."""
        return self._update(
            db, namespace=namespace, key=key, value=spec_for(namespace, key).default
        )

    @internal
    def backup_folder(self, db: DBSession) -> str:
        """Internal helper: where backups are written (empty = the default folder)."""
        return str(self.value(db, namespace=NS_BACKUP, key="folder") or "")

    def _row(self, db: DBSession, namespace: str, key: str) -> Setting | None:
        return db.execute(
            select(Setting).where(Setting.namespace == namespace, Setting.key == key)
        ).scalar_one_or_none()


def _kind_of(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, (dict, list)):
        return "json"
    return "str"


def _decode(raw: str, kind: str) -> Any:
    """Decode a stored JSON value; a corrupt row falls back to the default."""
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if kind == "bool" and not isinstance(value, bool):
        return bool(value)
    if kind == "int" and not isinstance(value, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    return value


def _is_valid(spec: SettingSpec, value: Any) -> bool:
    try:
        spec.validate(value)
    except (ValueError, TypeError):
        return False
    return True


def _current_user_id() -> int | None:
    session = current()
    return None if session is None else session.user_id
