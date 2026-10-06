"""Merge per-page extractions into one project-level record. Pure functions, no I/O."""

import re
from collections import defaultdict
from collections.abc import Iterable

from .schema import OpeningSummary, PageResult, ProjectData, Room, RoomSummary

_TRAILING_NUMBER = re.compile(r"[\s\-_.]*\d+[a-z]?$", re.IGNORECASE)


def _norm(s: str) -> str:
    return " ".join(s.upper().split())


def room_type(name: str) -> str:
    """'BED 1' -> 'BED', 'Bedroom 2a' -> 'BEDROOM', 'LIVING ROOM' -> 'LIVING ROOM'."""
    return _TRAILING_NUMBER.sub("", _norm(name)) or "UNKNOWN"


def dedupe_text(items: Iterable[str]) -> list[str]:
    """Case- and whitespace-insensitive, order-preserving, lowercased."""
    seen: set = set()
    out: list[str] = []
    for s in items:
        k = " ".join(s.lower().split())
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def dedupe_rooms(rooms: Iterable[Room]) -> list[Room]:
    """The same room is often drawn on several sheets (plan, electrical, demolition).

    Group by label. If any copy carries dimensions, drop the copies that don't. Then two copies
    with the same label and the same dimensions are one room; different dimensions are different
    rooms (two storeys can both have a 'BED 1')."""
    by_name: dict[str, list[Room]] = defaultdict(list)
    for r in rooms:
        by_name[_norm(r.name)].append(r)
    out: list[Room] = []
    for group in by_name.values():
        with_dims = [r for r in group if r.dimensions]
        candidates = with_dims or group
        seen: set = set()
        for r in candidates:
            key = _norm(r.dimensions or "")
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
    return out


def consolidate(results: Iterable[PageResult], source: str) -> ProjectData:
    results = sorted(results, key=lambda r: r.page)
    good = [r for r in results if r.ok and r.data is not None]

    pages_by_type: dict[str, list[int]] = defaultdict(list)
    raw_rooms: list[Room] = []
    door_count = window_count = 0
    door_types: list[str] = []
    window_types: list[str] = []
    fixtures: list[str] = []
    materials: list[str] = []
    notes: list[str] = []
    scales: list[str] = []
    project = None

    for r in good:
        d = r.data
        assert d is not None
        pages_by_type[d.page_type].append(r.page)
        if d.scale:
            scales.append(d.scale)
        if d.project and project is None:
            project = d.project.strip()
        if d.page_type == "floor_plan":
            raw_rooms.extend(d.rooms)
            door_count += d.doors.count
            door_types.extend(d.doors.types)
            window_count += d.windows.count
            window_types.extend(d.windows.types)
            fixtures.extend(d.fixtures)
        materials.extend(d.materials)
        notes.extend(d.notes)

    rooms = dedupe_rooms(raw_rooms)
    by_type: dict[str, int] = defaultdict(int)
    for r in rooms:
        by_type[room_type(r.name)] += 1
    total_area = round(sum(r.area_sqm for r in rooms if r.area_sqm is not None), 2)

    return ProjectData(
        source=source,
        project=project,
        scales=dedupe_text(scales),
        pages_by_type=dict(pages_by_type),
        rooms=RoomSummary(count=len(rooms), total_area_sqm=total_area, by_type=dict(by_type), rooms=rooms),
        doors=OpeningSummary(count=door_count, types=dedupe_text(door_types)),
        windows=OpeningSummary(count=window_count, types=dedupe_text(window_types)),
        fixtures=dedupe_text(fixtures),
        materials=dedupe_text(materials),
        notes=dedupe_text(notes),
        pages=results,
        failed_pages=[r.page for r in results if not r.ok],
    )


def summary(p: ProjectData) -> str:
    """Short human-readable digest for the terminal."""
    lines = [
        f"Source:   {p.source}",
        f"Project:  {p.project or '-'}",
        f"Pages:    {len(p.pages)} ({len(p.failed_pages)} failed)"
        + (f" failed: {p.failed_pages}" if p.failed_pages else ""),
        "By type:  " + (", ".join(f"{k} {v}" for k, v in sorted(p.pages_by_type.items())) or "-"),
        f"Scales:   {', '.join(p.scales) or '-'}",
        f"Rooms:    {p.rooms.count}, {p.rooms.total_area_sqm} sqm"
        + (" (" + ", ".join(f"{k} x{v}" for k, v in sorted(p.rooms.by_type.items())) + ")" if p.rooms.by_type else ""),
        f"Doors:    {p.doors.count}" + (f" ({', '.join(p.doors.types)})" if p.doors.types else ""),
        f"Windows:  {p.windows.count}" + (f" ({', '.join(p.windows.types)})" if p.windows.types else ""),
        f"Fixtures: {', '.join(p.fixtures) or '-'}",
        f"Materials: {', '.join(p.materials) or '-'}",
    ]
    if p.notes:
        lines.append("Notes:")
        lines.extend(f"  - {n}" for n in p.notes)
    return "\n".join(lines)
