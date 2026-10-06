"""blueprint-extract plan.pdf [-o out.json] [--pages 1-3] [--summary] [--dry-run]"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import __version__
from .consolidate import summary
from .pipeline import extract_sync
from .render import page_count, parse_pages, render_pages
from .vision import OpenAIVision, Vision


def build_vision(model: str | None, effort: str) -> Vision:
    return OpenAIVision(model=model, effort=effort)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="blueprint-extract", description=__doc__)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="write JSON here instead of stdout")
    ap.add_argument("--pages", help="1-based, e.g. '1-3,5'. Default: all")
    ap.add_argument("--model", help="vision model; default $OPENAI_MODEL or gpt-5-mini")
    ap.add_argument(
        "--effort",
        default="low",
        choices=["minimal", "low", "medium", "high"],
        help="reasoning effort for gpt-5 family models",
    )
    ap.add_argument("--max-side", type=int, default=2000, help="render so the longer side is this many px")
    ap.add_argument("--concurrency", type=int, default=4, help="pages in flight at once")
    ap.add_argument("--summary", action="store_true", help="print a short digest to stderr")
    ap.add_argument("--dry-run", action="store_true", help="render only; report pages and sizes, call no model")
    ap.add_argument("--version", action="version", version=__version__)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    a = parse_args(argv)
    if not a.pdf.is_file():
        print(f"error: {a.pdf} is not a file", file=sys.stderr)
        return 2
    try:
        pages = parse_pages(a.pages, page_count(a.pdf)) if a.pages else None
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if a.dry_run:
        for p in render_pages(a.pdf, pages=pages, max_side=a.max_side):
            print(f"page {p.number}: {p.width}x{p.height} px, {len(p.png) // 1024} KB")
        return 0

    if not os.getenv("OPENAI_API_KEY"):
        print("error: OPENAI_API_KEY is not set (put it in .env or the environment)", file=sys.stderr)
        return 2

    result = extract_sync(
        a.pdf, build_vision(a.model, a.effort), pages=pages, max_side=a.max_side, concurrency=a.concurrency
    )
    text = result.model_dump_json(indent=2)
    if a.output:
        a.output.write_text(text)
    else:
        print(text)
    ok = len(result.pages) - len(result.failed_pages)
    print(f"{ok}/{len(result.pages)} pages extracted", file=sys.stderr)
    if a.summary:
        print(summary(result), file=sys.stderr)
    for r in result.pages:
        if not r.ok:
            print(f"page {r.page}: {r.error}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
