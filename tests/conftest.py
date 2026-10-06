import asyncio
from pathlib import Path

import pytest

from blueprint_extract.schema import Openings, PageExtraction, Room

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_plan.pdf"


def make_page(page_type: str = "floor_plan", **over) -> PageExtraction:
    base = {
        "page_type": page_type,
        "project": "12 Example Street",
        "title": "GROUND FLOOR PLAN" if page_type == "floor_plan" else "FRONT ELEVATION",
        "scale": "1:100",
        "rooms": [
            Room(name="BED 1", dimensions="4.0 x 4.0", area_sqm=16.0),
            Room(name="BED 2", dimensions="4.0 x 4.0", area_sqm=16.0),
            Room(name="BATH", dimensions="3.0 x 4.0", area_sqm=12.0),
            Room(name="LIVING", dimensions="6.7 x 4.0", area_sqm=26.8),
            Room(name="KITCHEN", dimensions="4.3 x 4.0", area_sqm=17.2),
        ]
        if page_type == "floor_plan"
        else [],
        "doors": Openings(count=5, types=["entry", "internal"])
        if page_type == "floor_plan"
        else Openings(count=1, types=["entry"]),
        "windows": Openings(count=6, types=["sliding"])
        if page_type == "floor_plan"
        else Openings(count=2, types=["sliding"]),
        "fixtures": ["wc", "basin", "bath", "kitchen bench", "robe"] if page_type == "floor_plan" else [],
        "materials": [] if page_type == "floor_plan" else ["brick veneer", "colorbond roof"],
        "text_labels": ["11 000", "8 000"],
        "notes": ["existing wall to be removed"] if page_type == "floor_plan" else [],
        "confidence": 0.9,
    }
    base.update(over)
    return PageExtraction(**base)


class FakeVision:
    """Scripted responses per page. An Exception value is raised instead of returned."""

    def __init__(self, responses: dict[int, PageExtraction | Exception], delay: float = 0.0):
        self.responses = responses
        self.delay = delay
        self.calls: list = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def describe(self, png: bytes, page: int):
        self.calls.append(page)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.delay)
            r = self.responses[page]
            if isinstance(r, Exception):
                raise r
            return r, 100
        finally:
            self.in_flight -= 1


@pytest.fixture
def sample_pdf() -> Path:
    assert SAMPLE.exists(), "run examples/make_sample.py first"
    return SAMPLE


@pytest.fixture
def two_page_vision() -> FakeVision:
    return FakeVision({1: make_page("floor_plan"), 2: make_page("elevation")})
