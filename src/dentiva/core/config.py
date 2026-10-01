"""Application configuration: the catalogue of settings and their defaults.

Settings live in the ``settings`` table (one row per namespace/key). This module
is the **catalogue**: it declares every key the product understands, its type,
its default and whether the value is sensitive. Nothing here reads the database,
so the catalogue can be unit-tested on its own and the UI can build a settings
screen without hard-coding key strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Value kinds understood by the settings store.
KIND_BOOL = "bool"
KIND_INT = "int"
KIND_STR = "str"
KIND_JSON = "json"

#: Namespaces.
NS_APP = "app"
NS_SECURITY = "security"
NS_BACKUP = "backup"
NS_PRINT = "print"
NS_UI = "ui"
NS_CLINICAL = "clinical"


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """One configurable value."""

    namespace: str
    key: str
    default: Any
    kind: str = KIND_STR
    label: str = ""
    description: str = ""
    sensitive: bool = False
    options: tuple[Any, ...] = ()
    minimum: int | None = None
    maximum: int | None = None

    @property
    def path(self) -> tuple[str, str]:
        return (self.namespace, self.key)

    def validate(self, value: Any) -> Any:
        """Coerce *value* to the declared kind and reject out-of-range values."""
        if self.kind is KIND_BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{self.label or self.key} must be true or false.")
            return value
        if self.kind is KIND_INT:
            number = int(value)  # type: ignore[arg-type]
            if self.minimum is not None and number < self.minimum:
                raise ValueError(f"{self.label or self.key} cannot be below {self.minimum}.")
            if self.maximum is not None and number > self.maximum:
                raise ValueError(f"{self.label or self.key} cannot be above {self.maximum}.")
            if self.options and number not in self.options:
                raise ValueError(
                    f"{self.label or self.key} must be one of: "
                    + ", ".join(str(option) for option in self.options)
                    + "."
                )
            return number
        if self.kind is KIND_JSON:
            if not isinstance(value, (dict, list)):
                raise ValueError(f"{self.label or self.key} must be structured data.")
            return value
        text = str(value)
        if self.options and text not in self.options:
            raise ValueError(
                f"{self.label or self.key} must be one of: "
                + ", ".join(str(option) for option in self.options)
                + "."
            )
        return text


SETTING_SPECS: tuple[SettingSpec, ...] = (
    # -- application --------------------------------------------------------
    SettingSpec(
        NS_APP,
        "language",
        "en",
        label="Interface language",
        description=(
            "The application chrome is English; patient content accepts "
            "Bangla and any Unicode text."
        ),
        options=("en",),
    ),
    SettingSpec(
        NS_APP,
        "date_format",
        "dd MMM yyyy",
        label="Date format",
        options=("dd MMM yyyy", "dd/MM/yyyy", "yyyy-MM-dd"),
    ),
    SettingSpec(
        NS_APP, "time_format", "hh:mm AP", label="Time format", options=("hh:mm AP", "HH:mm")
    ),
    # -- security ------------------------------------------------------------
    SettingSpec(
        NS_SECURITY,
        "auto_lock_minutes",
        15,
        KIND_INT,
        label="Auto-lock after",
        description=(
            "Lock the workstation after this many minutes of inactivity. Unsaved work is kept."
        ),
        options=(5, 10, 15, 30),
        minimum=5,
        maximum=30,
    ),
    SettingSpec(
        NS_SECURITY,
        "require_reauth_for_sensitive",
        True,
        KIND_BOOL,
        label="Ask for the password again on sensitive actions",
    ),
    SettingSpec(
        NS_SECURITY,
        "min_password_length",
        10,
        KIND_INT,
        label="Minimum password length",
        minimum=8,
        maximum=64,
    ),
    # -- backups -------------------------------------------------------------
    SettingSpec(
        NS_BACKUP,
        "schedule_days",
        7,
        KIND_INT,
        label="Automatic backup every",
        description="0 disables scheduled backups; a manual backup is always available.",
        options=(0, 7, 15, 30),
    ),
    SettingSpec(
        NS_BACKUP,
        "folder",
        "",
        label="Backup folder",
        description="Chosen with a folder picker; never typed by hand.",
    ),
    SettingSpec(
        NS_BACKUP, "keep_last", 10, KIND_INT, label="Keep this many backups", minimum=1, maximum=100
    ),
    SettingSpec(NS_BACKUP, "last_run_on", "", label="Last automatic backup (local date)"),
    SettingSpec(
        NS_BACKUP,
        "verify_after_write",
        True,
        KIND_BOOL,
        label="Verify every backup after writing it",
    ),
    # -- printing ------------------------------------------------------------
    SettingSpec(NS_PRINT, "prescription_profile", "A4 prescription", label="Prescription paper"),
    SettingSpec(NS_PRINT, "invoice_profile", "A4 invoice", label="Invoice paper"),
    SettingSpec(NS_PRINT, "receipt_profile", "80 mm receipt", label="Receipt paper"),
    SettingSpec(NS_PRINT, "copies", 1, KIND_INT, label="Default copies", minimum=1, maximum=5),
    SettingSpec(NS_PRINT, "show_signature_area", True, KIND_BOOL, label="Reserve a signature area"),
    # -- interface -----------------------------------------------------------
    SettingSpec(
        NS_UI,
        "theme",
        "light",
        label="Theme",
        options=("light", "dark", "system"),
    ),
    SettingSpec(
        NS_UI, "density", "comfortable", label="Layout density", options=("comfortable", "compact")
    ),
    SettingSpec(
        NS_UI,
        "start_screen",
        "dashboard",
        label="Screen to open on start",
        options=("dashboard", "patients", "appointments", "queue"),
    ),
    SettingSpec(
        NS_UI,
        "grid_columns_1366",
        3,
        KIND_INT,
        label="Cards per row at 1366 px",
        minimum=1,
        maximum=6,
    ),
    # -- clinical ------------------------------------------------------------
    SettingSpec(
        NS_CLINICAL,
        "tooth_numbering",
        "fdi",
        label="Tooth numbering",
        description="FDI two-digit notation is the documented convention used by the chart.",
        options=("fdi",),
    ),
    SettingSpec(
        NS_CLINICAL,
        "default_dentition",
        "adult",
        label="Default dentition",
        options=("adult", "pediatric"),
    ),
    SettingSpec(
        NS_CLINICAL,
        "followup_default_days",
        7,
        KIND_INT,
        label="Default review interval (days)",
        minimum=1,
        maximum=365,
    ),
)

SPECS_BY_PATH: dict[tuple[str, str], SettingSpec] = {spec.path: spec for spec in SETTING_SPECS}


@dataclass(frozen=True, slots=True)
class AppConfig:
    """A resolved snapshot of every setting, for code that needs several at once."""

    values: dict[tuple[str, str], Any] = field(default_factory=dict)

    def get(self, namespace: str, key: str) -> Any:
        """Return the configured value, falling back to the declared default."""
        spec = SPECS_BY_PATH.get((namespace, key))
        if spec is None:
            raise KeyError(f"Unknown setting: {namespace}.{key}")
        return self.values.get((namespace, key), spec.default)

    def as_int(self, namespace: str, key: str) -> int:
        return int(self.get(namespace, key))

    def as_bool(self, namespace: str, key: str) -> bool:
        return bool(self.get(namespace, key))

    def as_str(self, namespace: str, key: str) -> str:
        return str(self.get(namespace, key))

    @classmethod
    def defaults(cls) -> AppConfig:
        """A snapshot containing only the declared defaults (used before set-up)."""
        return cls(values={spec.path: spec.default for spec in SETTING_SPECS})

    def replace(self, changes: dict[tuple[str, str], Any]) -> AppConfig:
        """Return a copy with *changes* applied (values are validated first)."""
        merged = dict(self.values)
        for path, value in changes.items():
            spec = SPECS_BY_PATH.get(path)
            if spec is None:
                raise KeyError(f"Unknown setting: {path[0]}.{path[1]}")
            merged[path] = spec.validate(value)
        return AppConfig(values=merged)


def spec_for(namespace: str, key: str) -> SettingSpec:
    """The declaration of one setting (raises ``KeyError`` if unknown)."""
    return SPECS_BY_PATH[(namespace, key)]


def auto_lock_options() -> tuple[int, ...]:
    """The auto-lock choices offered to the user, from the catalogue."""
    spec = SPECS_BY_PATH[(NS_SECURITY, "auto_lock_minutes")]
    return tuple(int(option) for option in spec.options)


def backup_schedule_options() -> tuple[int, ...]:
    """The scheduled-backup choices (0 = off)."""
    spec = SPECS_BY_PATH[(NS_BACKUP, "schedule_days")]
    return tuple(int(option) for option in spec.options)
