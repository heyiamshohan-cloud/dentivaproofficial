"""Paging primitives shared by repositories, services and the UI (REQ-PFM-004).

Two small, immutable value objects keep pagination honest:

``PageRequest``
    What the caller asked for (page number and page size), already clamped to
    sane bounds so a hostile or drifted page size can never make the database
    read an entire table into memory.

``Page``
    What came back: the rows for the requested page plus the total number of
    rows that match the filter, so the UI can render "showing 26–50 of 1 204"
    and calculate the last page without a second query.

Nothing here knows about SQL or Qt — it is pure data, which makes paging
behaviour testable without a database or a GUI.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

#: Page sizes offered by the UI. They are deliberately small enough that an
#: unlimited patient register stays responsive (REQ-SCL-002).
PAGE_SIZES: tuple[int, ...] = (10, 25, 50, 100)

#: Hard ceiling: a page size above this is clamped rather than honoured.
MAX_PAGE_SIZE = 500

DEFAULT_PAGE_SIZE = 25

ItemT = TypeVar("ItemT")


@dataclass(frozen=True, slots=True)
class PageRequest:
    """A validated request for one page of a result set."""

    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    sort_key: str | None = None
    descending: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "page", max(1, int(self.page)))
        object.__setattr__(self, "page_size", min(MAX_PAGE_SIZE, max(1, int(self.page_size))))

    @property
    def offset(self) -> int:
        """SQL OFFSET for this page."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL LIMIT for this page."""
        return self.page_size

    def for_page(self, page: int) -> PageRequest:
        """Return a copy of this request pointing at another page."""
        return PageRequest(
            page=page,
            page_size=self.page_size,
            sort_key=self.sort_key,
            descending=self.descending,
        )

    def sorted_by(self, key: str, *, descending: bool = False) -> PageRequest:
        """Return a copy with a new sort order (page resets to the first)."""
        return PageRequest(page=1, page_size=self.page_size, sort_key=key, descending=descending)

    def as_slice(self) -> slice:
        """Python slice equivalent, for in-memory paging of small lists."""
        start = self.offset
        return slice(start, start + self.page_size)


@dataclass(frozen=True, slots=True)
class Page(Generic[ItemT]):
    """One page of results plus the totals needed to render paging controls."""

    items: tuple[ItemT, ...]
    total: int = 0
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        object.__setattr__(self, "total", max(0, int(self.total)))
        object.__setattr__(self, "page", max(1, int(self.page)))
        object.__setattr__(self, "page_size", max(1, int(self.page_size)))

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[ItemT]:  # type: ignore[override]
        return iter(self.items)

    def __bool__(self) -> bool:
        return bool(self.items)

    @property
    def is_empty(self) -> bool:
        return not self.items

    @property
    def last_page(self) -> int:
        return max(1, -(-self.total // self.page_size))

    @property
    def first_item(self) -> int:
        """1-based index of the first row on this page (0 when empty)."""
        return 0 if not self.total else (self.page - 1) * self.page_size + 1

    @property
    def last_item(self) -> int:
        """1-based index of the last row on this page."""
        return min(self.page * self.page_size, self.total)

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.last_page

    def summary(self) -> str:
        """Human readable 'Showing 26–50 of 1 204' style text."""
        if not self.total:
            return "No records"
        return f"Showing {self.first_item}–{self.last_item} of {self.total}"

    @classmethod
    def from_sequence(
        cls, rows: Sequence[ItemT], request: PageRequest, *, total: int | None = None
    ) -> Page[ItemT]:
        """Page an in-memory sequence (used by tests and small catalogs)."""
        count = len(rows) if total is None else total
        return cls(
            items=tuple(rows[request.as_slice()]),
            total=count,
            page=request.page,
            page_size=request.page_size,
        )

    @classmethod
    def empty(cls, page_size: int = DEFAULT_PAGE_SIZE) -> Page[Any]:
        return cls(items=(), total=0, page=1, page_size=page_size)
