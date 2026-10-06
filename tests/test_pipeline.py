import asyncio

import pytest

from blueprint_extract.pipeline import extract, extract_sync
from tests.conftest import FakeVision, make_page


def test_extract_whole_document(sample_pdf, two_page_vision):
    p = extract_sync(sample_pdf, two_page_vision)
    assert p.source == "sample_plan.pdf"
    assert sorted(two_page_vision.calls) == [1, 2]
    assert p.failed_pages == [] and p.rooms.count == 5 and p.materials == ["brick veneer", "colorbond roof"]
    assert all(r.tokens == 100 for r in p.pages)


def test_extract_bytes_source_named_upload(sample_pdf, two_page_vision):
    p = extract_sync(sample_pdf.read_bytes(), two_page_vision, pages=[1])
    assert p.source == "upload" and [r.page for r in p.pages] == [1]
    p = extract_sync(sample_pdf.read_bytes(), two_page_vision, pages=[1], name="given.pdf")
    assert p.source == "given.pdf"


def test_one_failing_page_does_not_fail_the_document(sample_pdf):
    v = FakeVision({1: make_page(), 2: RuntimeError("model exploded")})
    p = extract_sync(sample_pdf, v)
    assert p.failed_pages == [2]
    assert p.pages[1].ok is False and p.pages[1].error == "RuntimeError: model exploded"
    assert p.rooms.count == 5


def test_concurrency_is_bounded(sample_pdf):
    v = FakeVision({1: make_page(), 2: make_page("elevation")}, delay=0.05)
    asyncio.run(extract(sample_pdf, v, concurrency=1))
    assert v.max_in_flight == 1
    v = FakeVision({1: make_page(), 2: make_page("elevation")}, delay=0.05)
    asyncio.run(extract(sample_pdf, v, concurrency=4))
    assert v.max_in_flight == 2


def test_bad_arguments(sample_pdf, two_page_vision):
    with pytest.raises(ValueError):
        extract_sync(sample_pdf, two_page_vision, concurrency=0)
    with pytest.raises(ValueError):
        extract_sync(sample_pdf, two_page_vision, pages=[9])
