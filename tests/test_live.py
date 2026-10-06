"""Hits the real model. Skipped unless OPENAI_API_KEY is set.  uv run pytest tests/test_live.py -s"""

import os

import pytest
from dotenv import load_dotenv

from blueprint_extract import OpenAIVision, extract_sync
from blueprint_extract.consolidate import summary

load_dotenv()
pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")


def test_sample_plan_end_to_end(sample_pdf):
    p = extract_sync(sample_pdf, OpenAIVision(), concurrency=2)
    print("\n" + summary(p))
    assert p.failed_pages == []
    assert p.pages_by_type.get("floor_plan") == [1]
    assert p.pages_by_type.get("elevation") == [2]
    names = {r.name.upper() for r in p.rooms.rooms}
    assert {"BED 1", "BED 2", "BATH", "LIVING", "KITCHEN"} <= names
    assert 4 <= p.doors.count <= 6
    assert 5 <= p.windows.count <= 7
    assert any("brick" in m for m in p.materials)
    assert any("removed" in n for n in p.notes)
