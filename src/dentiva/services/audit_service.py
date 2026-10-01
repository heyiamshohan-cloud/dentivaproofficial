"""Append-only audit log with a SHA-256 hash chain (ADR-0009, docs/05 §5).

Three independent layers make the trail trustworthy:

1. **SQLite triggers** (created in migration ``0001``) reject UPDATE and DELETE
   outright, so the log cannot be edited through the database at all.
2. **A hash chain** — every row stores the previous row's hash, so a row that is
   inserted or altered out of band is detectable by :meth:`AuditService.verify`.
3. **Redaction** — secrets never reach the log in the first place.

Verification is exposed in System Health and is run before/after every backup
and restore.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dentiva.core.clock import local_now, utc_now
from dentiva.core.paging import Page, PageRequest
from dentiva.data.models.ops import AuditLog

#: Keys whose values are replaced before a payload is persisted.
REDACTED_KEYS: tuple[str, ...] = (
    "password",
    "password_hash",
    "new_password",
    "current_password",
    "hash",
    "token",
    "secret",
    "key",
    "activation",
    "activation_code",
)
REDACTED_MARK = "«redacted»"

#: Severity levels.
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_SECURITY = "security"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """A read-only view of one audit row (never the ORM object)."""

    id: int
    ts_utc: datetime
    ts_local: str
    actor_user_id: int | None
    actor_username: str
    actor_role_names: str
    action: str
    entity: str
    entity_id: int | None
    patient_id: int | None
    summary: str
    severity: str
    source: str
    before: Mapping[str, Any]
    after: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AuditChainReport:
    """Result of verifying the hash chain."""

    checked: int
    intact: bool
    first_broken_id: int | None = None
    detail: str = ""

    def describe(self) -> str:
        if self.intact:
            return f"audit chain intact ({self.checked} entries verified)"
        return (
            f"audit chain broken at entry {self.first_broken_id}: {self.detail} "
            f"({self.checked} entries checked)"
        )


def _current_actor() -> Any:
    """The session of the signed-in user (``None`` for a background job)."""
    from dentiva.security.session import current

    return current()


def redact(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a copy of *payload* with every secret-looking value removed."""
    if not payload:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = str(key).lower()
        if any(marker in lowered for marker in REDACTED_KEYS):
            cleaned[key] = REDACTED_MARK
        elif isinstance(value, Mapping):
            cleaned[key] = redact(value)
        else:
            cleaned[key] = value
    return cleaned


class AuditService:
    """Writes and verifies audit entries. All methods join the caller's session."""

    def record(
        self,
        session: Session,
        *,
        action: str,
        entity: str = "",
        entity_id: int | None = None,
        summary: str = "",
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
        severity: str = SEVERITY_INFO,
        patient_id: int | None = None,
        visit_id: int | None = None,
        actor: Any = None,
        source: str = "app",
        business_id: int | None = None,
    ) -> AuditLog:
        """Append one audit entry, linked to the previous one by hash.

        ``actor`` defaults to the signed-in session, so a caller cannot forget
        to say who did it; pass an explicit actor only for automated jobs.
        """
        resolved_actor = actor if actor is not None else _current_actor()
        previous_hash = self._last_hash(session)
        now = utc_now()
        row = AuditLog(
            ts_utc=now,
            ts_local=local_now().isoformat(timespec="seconds"),
            business_id=business_id
            if business_id is not None
            else getattr(resolved_actor, "business_id", None),
            actor_user_id=getattr(resolved_actor, "user_id", None),
            actor_username=getattr(resolved_actor, "username", "") or "system",
            actor_role_names=", ".join(getattr(resolved_actor, "roles", ()) or ()),
            action=action,
            entity=entity,
            entity_id=entity_id,
            patient_id=patient_id,
            visit_id=visit_id,
            summary=summary,
            before_json=self._dump(before),
            after_json=self._dump(after),
            severity=severity,
            source=source,
            session_id=getattr(resolved_actor, "session_id", None),
            prev_hash=previous_hash,
            row_hash="",
        )
        row.row_hash = self._row_hash(row)
        session.add(row)
        session.flush()
        return row

    def verify(self, session: Session, *, limit: int | None = None) -> AuditChainReport:
        """Walk the chain from the oldest entry and report the first broken link."""
        statement = select(AuditLog).order_by(AuditLog.id)
        if limit:
            statement = statement.limit(limit)
        rows: Sequence[AuditLog] = session.execute(statement).scalars().all()
        expected_previous = ""
        for row in rows:
            if row.prev_hash != expected_previous:
                return AuditChainReport(
                    checked=len(rows),
                    intact=False,
                    first_broken_id=row.id,
                    detail=(
                        f"prev_hash does not match the previous row "
                        f"(expected {expected_previous or 'empty'}, found {row.prev_hash})"
                    ),
                )
            if self._row_hash(row) != row.row_hash:
                return AuditChainReport(
                    checked=len(rows),
                    intact=False,
                    first_broken_id=row.id,
                    detail="row_hash does not match the stored content",
                )
            expected_previous = row.row_hash
        return AuditChainReport(checked=len(rows), intact=True)

    def count(self, session: Session) -> int:
        return int(session.execute(select(func.count()).select_from(AuditLog)).scalar() or 0)

    def search(
        self,
        session: Session,
        *,
        request: PageRequest | None = None,
        action: str | None = None,
        entity: str | None = None,
        entity_id: int | None = None,
        actor_user_id: int | None = None,
        patient_id: int | None = None,
        severity: str | None = None,
        text: str | None = None,
    ) -> Page[AuditEntry]:
        """Return one page of audit entries (oldest first within the page)."""
        page_request = request or PageRequest()
        statement = select(AuditLog)
        if action:
            statement = statement.where(AuditLog.action == action)
        if entity:
            statement = statement.where(AuditLog.entity == entity)
        if entity_id is not None:
            statement = statement.where(AuditLog.entity_id == entity_id)
        if actor_user_id is not None:
            statement = statement.where(AuditLog.actor_user_id == actor_user_id)
        if patient_id is not None:
            statement = statement.where(AuditLog.patient_id == patient_id)
        if severity:
            statement = statement.where(AuditLog.severity == severity)
        if text:
            pattern = f"%{text}%"
            statement = statement.where(
                AuditLog.summary.like(pattern) | AuditLog.action.like(pattern)
            )
        total = int(
            session.execute(select(func.count()).select_from(statement.subquery())).scalar() or 0
        )
        rows = (
            session.execute(
                statement.order_by(AuditLog.id.desc())
                .offset(page_request.offset)
                .limit(page_request.limit)
            )
            .scalars()
            .all()
        )
        entries = [self._to_entry(row) for row in rows]
        return Page(
            items=tuple(entries),
            total=total,
            page=page_request.page,
            page_size=page_request.page_size,
        )

    @staticmethod
    def _to_entry(row: AuditLog) -> AuditEntry:
        return AuditEntry(
            id=row.id,
            ts_utc=row.ts_utc,
            ts_local=row.ts_local or "",
            actor_user_id=row.actor_user_id,
            actor_username=row.actor_username or "",
            actor_role_names=row.actor_role_names or "",
            action=row.action,
            entity=row.entity or "",
            entity_id=row.entity_id,
            patient_id=row.patient_id,
            summary=row.summary or "",
            severity=row.severity,
            source=row.source,
            before=_load(row.before_json),
            after=_load(row.after_json),
        )

    @staticmethod
    def _dump(payload: Mapping[str, Any] | None) -> str | None:
        if payload is None:
            return None
        return json.dumps(redact(payload), ensure_ascii=False, sort_keys=True, default=str)

    @staticmethod
    def _last_hash(session: Session) -> str:
        value = session.execute(
            select(AuditLog.row_hash).order_by(AuditLog.id.desc()).limit(1)
        ).scalar()
        return value or ""

    @staticmethod
    def _row_hash(row: AuditLog) -> str:
        """Hash over the row's immutable content plus the previous hash."""
        payload = "|".join(
            str(part)
            for part in (
                row.prev_hash,
                row.ts_utc.isoformat() if row.ts_utc else "",
                row.actor_user_id,
                row.actor_username,
                row.action,
                row.entity,
                row.entity_id,
                row.patient_id,
                row.summary,
                row.severity,
                row.source,
                row.before_json,
                row.after_json,
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load(raw: str | None) -> Mapping[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:  # pragma: no cover - defensive, rows are written by us
        return {"_unreadable": True}
    return data if isinstance(data, dict) else {"value": data}


def entry_ids(entries: Iterable[AuditEntry]) -> list[int]:
    return [entry.id for entry in entries]
