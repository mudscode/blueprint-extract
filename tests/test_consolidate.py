from blueprint_extract.consolidate import consolidate, dedupe_rooms, dedupe_text, room_type, summary
from blueprint_extract.schema import Openings, PageResult, Room
from tests.conftest import make_page


def test_room_type():
    assert room_type("BED 1") == "BED"
    assert room_type("bedroom 2a") == "BEDROOM"
    assert room_type("LIVING ROOM") == "LIVING ROOM"
    assert room_type("  W.I.R  ") == "W.I.R"
    assert room_type("3") == "UNKNOWN"


def test_dedupe_text():
    assert dedupe_text(["Brick Veneer", "brick  veneer", "", "Roof"]) == ["brick veneer", "roof"]


def test_dedupe_rooms_same_label_same_dims_is_one_room():
    rooms = dedupe_rooms(
        [Room(name="BED 1", dimensions="4 x 4", area_sqm=16), Room(name="bed 1", dimensions="4 X 4", area_sqm=None)]
    )
    assert len(rooms) == 1


def test_dedupe_rooms_same_label_different_dims_are_two_rooms():
    rooms = dedupe_rooms(
        [Room(name="BED 1", dimensions="4 x 4", area_sqm=16), Room(name="BED 1", dimensions="3 x 3", area_sqm=9)]
    )
    assert len(rooms) == 2


def test_dedupe_rooms_prefers_copies_with_dimensions():
    rooms = dedupe_rooms(
        [
            Room(name="BED 1", dimensions=None, area_sqm=None),
            Room(name="BED 1", dimensions="4 x 4", area_sqm=16),
            Room(name="BED 1", dimensions=None, area_sqm=None),
        ]
    )
    assert len(rooms) == 1 and rooms[0].dimensions == "4 x 4"


def test_dedupe_rooms_without_any_dims_keeps_one_per_label():
    rooms = dedupe_rooms(
        [Room(name="HALL", dimensions=None, area_sqm=None), Room(name="Hall", dimensions=None, area_sqm=None)]
    )
    assert len(rooms) == 1


def test_consolidate_two_good_pages():
    p = consolidate(
        [
            PageResult(page=1, ok=True, data=make_page("floor_plan"), tokens=10),
            PageResult(page=2, ok=True, data=make_page("elevation"), tokens=20),
        ],
        source="x.pdf",
    )
    assert p.project == "12 Example Street"
    assert p.pages_by_type == {"floor_plan": [1], "elevation": [2]}
    assert p.scales == ["1:100"]
    assert p.rooms.count == 5
    assert p.rooms.total_area_sqm == 88.0
    assert p.rooms.by_type == {"BED": 2, "BATH": 1, "LIVING": 1, "KITCHEN": 1}
    # openings and fixtures come from floor plans only; the elevation's door and windows are not added
    assert p.doors.count == 5 and p.doors.types == ["entry", "internal"]
    assert p.windows.count == 6
    assert p.fixtures == ["wc", "basin", "bath", "kitchen bench", "robe"]
    # materials and notes come from every page
    assert p.materials == ["brick veneer", "colorbond roof"]
    assert p.notes == ["existing wall to be removed"]
    assert p.failed_pages == []


def test_consolidate_sorts_pages_and_tracks_failures():
    p = consolidate(
        [PageResult(page=2, ok=False, error="VisionError: boom"), PageResult(page=1, ok=True, data=make_page())],
        source="x.pdf",
    )
    assert [r.page for r in p.pages] == [1, 2]
    assert p.failed_pages == [2]
    assert p.rooms.count == 5


def test_consolidate_two_floor_plans_merge_repeated_rooms_and_sum_openings():
    a = make_page("floor_plan")
    b = make_page(
        "floor_plan",
        title="ELECTRICAL PLAN",
        doors=Openings(count=0, types=[]),
        windows=Openings(count=0, types=[]),
        rooms=[Room(name="BED 1", dimensions=None, area_sqm=None)],
    )
    p = consolidate([PageResult(page=1, ok=True, data=a), PageResult(page=2, ok=True, data=b)], source="x")
    assert p.rooms.count == 5  # the dimensionless repeat of BED 1 collapsed into the real one
    assert p.doors.count == 5


def test_consolidate_area_ignores_rooms_without_area():
    page = make_page(
        rooms=[Room(name="A", dimensions=None, area_sqm=None), Room(name="B", dimensions="2 x 2", area_sqm=4)]
    )
    p = consolidate([PageResult(page=1, ok=True, data=page)], source="x")
    assert p.rooms.total_area_sqm == 4.0


def test_consolidate_empty():
    p = consolidate([], source="x")
    assert p.rooms.count == 0 and p.pages == [] and p.project is None and p.pages_by_type == {}


def test_summary_mentions_the_numbers():
    p = consolidate(
        [PageResult(page=1, ok=True, data=make_page()), PageResult(page=2, ok=False, error="x")], source="plan.pdf"
    )
    s = summary(p)
    assert "plan.pdf" in s and "Rooms:    5" in s and "88.0 sqm" in s and "failed: [2]" in s
    assert "existing wall to be removed" in s
