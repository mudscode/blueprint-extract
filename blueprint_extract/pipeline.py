"""Render, describe every page concurrently, consolidate."""

import asyncio
from collections.abc import Iterable
from pathlib import Path

from .consolidate import consolidate
from .render import Source, render_pages
from .schema import PageResult, ProjectData
from .vision import Vision


async def extract(
    source: Source,
    vision: Vision,
    pages: Iterable[int] | None = None,
    max_side: int = 2000,
    concurrency: int = 4,
    name: str | None = None,
) -> ProjectData:
    """One failing page never fails the document: it lands in failed_pages with its error."""
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    rendered = render_pages(source, pages=pages, max_side=max_side)
    sem = asyncio.Semaphore(concurrency)

    async def one(p) -> PageResult:
        async with sem:
            try:
                data, tokens = await vision.describe(p.png, p.number)
                return PageResult(page=p.number, ok=True, data=data, tokens=tokens)
            except Exception as e:
                return PageResult(page=p.number, ok=False, error=f"{type(e).__name__}: {e}")

    results = await asyncio.gather(*(one(p) for p in rendered))
    if name is None:
        name = "upload" if isinstance(source, (bytes, bytearray)) else Path(str(source)).name
    return consolidate(results, source=name)


def extract_sync(source: Source, vision: Vision, **kw) -> ProjectData:
    return asyncio.run(extract(source, vision, **kw))
