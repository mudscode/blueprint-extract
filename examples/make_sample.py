"""Draw a small synthetic two-sheet drawing set so the repo has a test input that belongs to nobody.

uv run python examples/make_sample.py          # writes examples/sample_plan.pdf
"""

from pathlib import Path

import pymupdf as fitz

OUT = Path(__file__).with_name("sample_plan.pdf")
W, H = 1190, 842  # A3 landscape in points
WALL = 2.2
THIN = 0.8


def text(page, x, y, s, size=11, bold=False):
    page.insert_text((x, y), s, fontsize=size, fontname="hebo" if bold else "helv")


def title_block(page, sheet, title, scale):
    s = page.new_shape()
    s.draw_rect(fitz.Rect(820, 660, 1150, 810))
    s.draw_line((820, 700), (1150, 700))
    s.draw_line((820, 760), (1150, 760))
    s.finish(width=1.2)
    s.commit()
    text(page, 830, 688, "SAMPLE DWELLING - SYNTHETIC TEST DRAWING", 12, True)
    text(page, 830, 725, "PROJECT: 12 EXAMPLE STREET, NOWHERE", 10)
    text(page, 830, 745, title, 13, True)
    text(page, 830, 785, f"SCALE {scale} @ A3", 10)
    text(page, 1010, 785, f"SHEET {sheet}", 10)
    text(page, 1010, 800, "DATE 10.2026", 8)


def door(s, x, y, size, direction):
    """Quarter-circle swing plus the leaf, like a plan symbol. direction: 'r','l','u','d'."""
    if direction == "r":
        s.draw_sector((x, y), (x + size, y), 90)
        s.draw_line((x, y), (x, y - size))
    elif direction == "l":
        s.draw_sector((x, y), (x - size, y), -90)
        s.draw_line((x, y), (x, y - size))
    elif direction == "d":
        s.draw_sector((x, y), (x, y + size), 90)
        s.draw_line((x, y), (x + size, y))
    else:
        s.draw_sector((x, y), (x, y - size), -90)
        s.draw_line((x, y), (x + size, y))


def window(s, x1, y1, x2, y2):
    """Thin double line in the wall."""
    if y1 == y2:
        s.draw_line((x1, y1 - 3), (x2, y2 - 3))
        s.draw_line((x1, y1 + 3), (x2, y2 + 3))
    else:
        s.draw_line((x1 - 3, y1), (x2 - 3, y2))
        s.draw_line((x1 + 3, y1), (x2 + 3, y2))


def floor_plan(page):
    text(page, 100, 70, "GROUND FLOOR PLAN", 16, True)
    # walls, 1:100 so 1 m = 10 pt * 2.835... keep it simple: 1 m = 60 pt
    s = page.new_shape()
    s.draw_rect(fitz.Rect(100, 100, 760, 580))  # outer 11.0 x 8.0 m
    s.draw_line((340, 100), (340, 340))  # bed1 | bed2
    s.draw_line((580, 100), (580, 340))  # bed2 | bath
    s.draw_line((100, 340), (760, 340))  # beds | living/kitchen
    s.draw_line((500, 340), (500, 580))  # living | kitchen
    s.finish(width=WALL)
    s.commit()

    # doors: 1 entry + 4 internal = 5
    s = page.new_shape()
    door(s, 180, 580, 50, "u")  # entry, bottom wall into living
    door(s, 200, 340, 45, "d")  # bed 1 -> living (swings down into living)
    door(s, 400, 340, 45, "d")  # bed 2 -> living
    door(s, 620, 340, 40, "d")  # bath -> kitchen side
    door(s, 500, 420, 45, "r")  # living -> kitchen
    s.finish(width=THIN)
    s.commit()

    # windows: 6
    s = page.new_shape()
    window(s, 140, 100, 260, 100)  # bed 1 top
    window(s, 400, 100, 520, 100)  # bed 2 top
    window(s, 620, 100, 700, 100)  # bath top
    window(s, 100, 400, 100, 520)  # living left
    window(s, 760, 400, 760, 520)  # kitchen right
    window(s, 560, 580, 700, 580)  # kitchen bottom
    s.finish(width=THIN)
    s.commit()

    # fixtures
    s = page.new_shape()
    s.draw_rect(fitz.Rect(600, 120, 630, 160))  # wc
    s.draw_rect(fitz.Rect(690, 120, 740, 160))  # basin
    s.draw_rect(fitz.Rect(600, 270, 740, 330))  # bath tub
    s.draw_rect(fitz.Rect(520, 360, 740, 400))  # kitchen bench
    s.draw_rect(fitz.Rect(110, 110, 150, 330))  # wardrobe bed 1
    s.finish(width=THIN)
    s.commit()
    text(page, 603, 175, "WC", 7)
    text(page, 693, 175, "BASIN", 7)
    text(page, 650, 303, "BATH", 7)
    text(page, 600, 383, "KITCHEN BENCH", 7)
    text(page, 112, 220, "ROBE", 7)

    # room labels with dimensions (metres)
    for x, y, name, dims in [
        (190, 210, "BED 1", "4.0 x 4.0"),
        (420, 210, "BED 2", "4.0 x 4.0"),
        (630, 220, "BATH", "3.0 x 4.0"),
        (260, 460, "LIVING", "6.7 x 4.0"),
        (590, 480, "KITCHEN", "4.3 x 4.0"),
    ]:
        text(page, x, y, name, 12, True)
        text(page, x, y + 16, dims, 9)

    # overall dimensions
    text(page, 400, 92, "11 000", 8)
    text(page, 72, 350, "8 000", 8)

    # a demolition note with dashed line
    s = page.new_shape()
    s.draw_line((340, 340), (340, 580))
    s.finish(width=THIN, dashes="[6 4] 0")
    s.commit()
    text(page, 300, 600, "EXISTING WALL TO BE REMOVED", 8)
    text(page, 100, 640, "NOTE: ALL DIMENSIONS IN MILLIMETRES UNLESS NOTED. NEW SLAB TO ENGINEER'S DETAIL.", 8)
    title_block(page, "A-01", "GROUND FLOOR PLAN", "1:100")


def elevation(page):
    text(page, 100, 70, "FRONT ELEVATION", 16, True)
    s = page.new_shape()
    s.draw_polyline([(150, 500), (150, 300), (400, 150), (650, 300), (650, 500), (150, 500)])  # house with gable
    s.draw_line((120, 500), (700, 500))  # ground line
    s.draw_rect(fitz.Rect(370, 400, 430, 500))  # door
    s.finish(width=WALL)
    s.commit()
    s = page.new_shape()
    s.draw_rect(fitz.Rect(200, 340, 290, 420))  # window
    s.draw_rect(fitz.Rect(510, 340, 600, 420))  # window
    s.draw_line((245, 340), (245, 420))
    s.draw_line((555, 340), (555, 420))
    s.finish(width=THIN)
    s.commit()
    text(page, 160, 530, "NATURAL GROUND LINE", 8)
    text(page, 420, 230, "COLORBOND ROOF, 22.5 DEG PITCH", 8)
    text(page, 160, 290, "BRICK VENEER", 8)
    text(page, 200, 335, "ALUMINIUM SLIDING WINDOW", 7)
    text(page, 360, 395, "ENTRY DOOR", 7)
    title_block(page, "A-02", "FRONT ELEVATION", "1:100")


def main() -> None:
    doc = fitz.open()
    floor_plan(doc.new_page(width=W, height=H))
    elevation(doc.new_page(width=W, height=H))
    doc.save(OUT, deflate=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
