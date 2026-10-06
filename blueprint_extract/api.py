"""POST a PDF, get ProjectData back.  uvicorn blueprint_extract.api:app"""

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile

from . import __version__
from .pipeline import extract
from .render import page_count, parse_pages
from .schema import ProjectData
from .vision import OpenAIVision, Vision

load_dotenv()
app = FastAPI(title="blueprint-extract", version=__version__)


def get_vision() -> Vision:
    return OpenAIVision()


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "openai_key": bool(os.getenv("OPENAI_API_KEY"))}


@app.post("/extract", response_model=ProjectData)
async def extract_pdf(
    file: UploadFile = File(...),
    pages: str | None = Query(None, description="1-based, e.g. '1-3,5'"),
    max_side: int = Query(2000, ge=100, le=4000),
    concurrency: int = Query(4, ge=1, le=16),
    vision: Vision = Depends(get_vision),
) -> ProjectData:
    data = await file.read()
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "not a PDF")
    try:
        page_list = parse_pages(pages, page_count(data)) if pages else None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return await extract(
        data, vision, pages=page_list, max_side=max_side, concurrency=concurrency, name=file.filename or "upload"
    )
