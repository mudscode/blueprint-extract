"""PDF pages to PNG bytes. Pure PyMuPDF, no model involved."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz

Source = str | Path | bytes | bytearray


@dataclass(frozen=True)
class RenderedPage:
    number: int  # 1-based
    png: bytes
    width: int
    height: int


def _open(source: Source) -> fitz.Document:
    if isinstance(source, (bytes, bytearray)):
        return fitz.open(stream=bytes(source), filetype="pdf")
    return fitz.open(str(source))


def page_count(source: Source) -> int:
    with _open(source) as doc:
        return len(doc)


def render_pages(source: Source, pages: Iterable[int] | None = None, max_side: int = 2000) -> list[RenderedPage]:
    """Render the given 1-based pages (all when None) so the longer side is max_side pixels.

    Vision APIs downscale anything larger than roughly 2000px anyway, so rendering bigger
    only costs upload time."""
    if max_side < 100:
        raise ValueError("max_side must be at least 100 pixels")
    with _open(source) as doc:
        n = len(doc)
        wanted = sorted(set(pages)) if pages is not None else list(range(1, n + 1))
        for p in wanted:
            if not 1 <= p <= n:
                raise ValueError(f"page {p} out of range 1..{n}")
        out = []
        for p in wanted:
            page = doc[p - 1]
            zoom = max_side / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            out.append(RenderedPage(number=p, png=pix.tobytes("png"), width=pix.width, height=pix.height))
    return out


def parse_pages(spec: str, n: int) -> list[int]:
    """'1-3,5,8-' -> [1, 2, 3, 5, 8, ..., n]. 1-based, inclusive, de-duplicated, sorted."""
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo = int(lo_s) if lo_s.strip() else 1
            hi = int(hi_s) if hi_s.strip() else n
        else:
            lo = hi = int(part)
        if lo < 1 or hi > n or lo > hi:
            raise ValueError(f"page range '{part}' is outside 1..{n}")
        pages.update(range(lo, hi + 1))
    if not pages:
        raise ValueError("no pages selected")
    return sorted(pages)
