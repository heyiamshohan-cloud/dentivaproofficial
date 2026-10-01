"""Paging primitives: clamping, totals and summaries (REQ-PFM-004, REQ-SCL-002)."""

from __future__ import annotations

import pytest

from dentiva.core.paging import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Page,
    PageRequest,
)


def test_page_request_clamps_hostile_values() -> None:
    assert PageRequest(page=0).page == 1
    assert PageRequest(page=-12).page == 1
    assert PageRequest(page_size=0).page_size == 1
    assert PageRequest(page_size=-5).page_size == 1
    assert PageRequest(page_size=10**9).page_size == MAX_PAGE_SIZE


def test_offset_and_limit_match_the_page() -> None:
    request = PageRequest(page=4, page_size=25)
    assert (request.offset, request.limit) == (75, 25)
    assert request.as_slice() == slice(75, 100)


def test_derived_requests_keep_the_page_size_and_sort() -> None:
    request = PageRequest(page=2, page_size=50, sort_key="name", descending=True)
    assert request.for_page(7) == PageRequest(
        page=7, page_size=50, sort_key="name", descending=True
    )
    changed = request.sorted_by("code")
    assert changed.page == 1
    assert (changed.sort_key, changed.descending) == ("code", False)


def test_page_maths_for_a_partial_last_page() -> None:
    page = Page(items=tuple(range(10)), total=1204, page=49, page_size=25)
    assert page.last_page == 49
    assert page.first_item == 1201
    assert page.last_item == 1204
    assert page.has_previous and not page.has_next
    assert page.summary() == "Showing 1201–1204 of 1204"
    assert len(page) == 10 and bool(page) and list(page)[-1] == 9


def test_empty_page() -> None:
    page = Page[str].empty()
    assert page.is_empty
    assert page.summary() == "No records"
    assert page.last_page == 1
    assert not page.has_previous and not page.has_next
    assert page.first_item == 0 and page.last_item == 0


def test_from_sequence_pages_in_memory_data() -> None:
    rows = [f"P-{index:04d}" for index in range(1, 61)]
    request = PageRequest(page=3, page_size=25)
    page = Page.from_sequence(rows, request, total=len(rows))
    assert page.items == tuple(rows[50:60])
    assert page.summary() == "Showing 51–60 of 60"
    assert not page.has_next


def test_page_is_immutable() -> None:
    page = Page(items=("a",), total=1)
    with pytest.raises(AttributeError):  # frozen dataclass
        page.page = 2  # type: ignore[misc]


def test_default_page_size_is_one_of_the_offered_sizes() -> None:
    from dentiva.core.paging import PAGE_SIZES

    assert DEFAULT_PAGE_SIZE in PAGE_SIZES
    assert all(size > 0 for size in PAGE_SIZES)
