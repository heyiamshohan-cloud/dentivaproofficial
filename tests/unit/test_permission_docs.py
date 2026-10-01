"""The permission catalogue and its documentation must not drift (REQ-DCM-002).

``docs/06-rbac-permissions.md`` is the human-readable contract for role editors;
``dentiva/domain/permissions.py`` is the runtime source of truth. A permission in
one and not the other is either an undocumented permission (a role editor cannot
grant it knowingly) or a documented one that does nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dentiva.domain.permissions import BY_CODE, PERMISSIONS

DOCS = Path(__file__).resolve().parents[2] / "docs" / "06-rbac-permissions.md"

#: ``patient.view`` — two dotted lowercase words; excludes file names and module paths.
CODE_PATTERN = re.compile(r"`([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)`")


@pytest.fixture(scope="module")
def documented() -> set[str]:
    if not DOCS.is_file():
        pytest.skip("docs/06 is not present")
    return {
        code
        for code in CODE_PATTERN.findall(DOCS.read_text(encoding="utf-8"))
        if not code.endswith(".py")  # file names are not permission codes
    }


def test_the_documented_catalogue_matches_the_implemented_one(documented: set[str]) -> None:
    implemented = set(BY_CODE)
    assert implemented - documented == set(), (
        f"permissions implemented but not documented in docs/06: {sorted(implemented - documented)}"
    )
    assert documented - implemented == set(), (
        f"permissions documented but not implemented: {sorted(documented - implemented)}"
    )


def test_the_catalogue_is_large_enough_to_be_granular(documented: set[str]) -> None:
    assert len(PERMISSIONS) >= 40
    assert len(documented) >= 40


def test_every_permission_is_documented_with_a_meaning() -> None:
    """A code alone is not documentation: each one needs a prose description."""
    for spec in PERMISSIONS:
        assert spec.description, f"{spec.code} has no description"
        assert spec.label, f"{spec.code} has no label"
        assert spec.group, f"{spec.code} has no group"
