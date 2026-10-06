# blueprint-extract

Architectural drawing PDFs in, structured JSON out. Each page is rendered to an image, read by a
vision model under a strict schema, then the pages are merged into one project record: rooms with
areas, door and window counts, fixtures, materials, notes, and which sheets are plans, elevations,
sections or details.

```
uv sync
cp .env.example .env            # add OPENAI_API_KEY
uv run blueprint-extract examples/sample_plan.pdf --summary -o out.json
```

```
Project:  12 Example Street, Nowhere
Pages:    2 (0 failed)
By type:  elevation 1, floor_plan 1
Rooms:    5, 88.0 sqm (BATH x1, BED x2, KITCHEN x1, LIVING x1)
Doors:    5 (entry, internal)
Windows:  6 (sliding)
Materials: brick veneer, colorbond roof
```

## Usage

CLI: `blueprint-extract plan.pdf [-o out.json] [--pages 1-3,5] [--model gpt-5-mini] [--summary] [--dry-run]`.
`--dry-run` renders pages and reports sizes without calling a model.

API: `uv run uvicorn blueprint_extract.api:app`, then `POST /extract` with a multipart `file` and
optional `?pages=1-3`. Returns the same JSON as the CLI.

Python:

```python
from blueprint_extract import extract_sync, OpenAIVision

data = extract_sync("plan.pdf", OpenAIVision(model="gpt-5-mini"), pages=[1, 2])
print(data.rooms.total_area_sqm, data.failed_pages)
```

## How it works

- `render.py` draws each page with PyMuPDF so the longer side is 2000 px. Bigger is wasted; the API downscales.
- `vision.py` sends one page per request to the OpenAI Responses API with `PageExtraction` as the output
  schema, so the model cannot return malformed JSON. Transient errors retry; refusals do not.
- `pipeline.py` runs pages concurrently under a semaphore. A failing page is recorded, not fatal.
- `consolidate.py` merges pages. Rooms repeated across sheets collapse by label and dimensions, so a plan
  and its electrical overlay count once while two storeys with a `BED 1` each count twice. Openings and
  fixtures are taken from floor plans only; materials and notes from every page.

## Output

`ProjectData`: `project`, `scales`, `pages_by_type`, `rooms{count,total_area_sqm,by_type,rooms[]}`,
`doors{count,types}`, `windows{count,types}`, `fixtures`, `materials`, `notes`, `pages[]` (the raw
per-page extraction plus `tokens` or `error`), `failed_pages`. Full schema in `blueprint_extract/schema.py`.

## Limits

Counts are what the model can see at 2000 px, so dense A1 sheets lose small symbols. Areas are only as
good as the printed dimensions. Scanned drawings with poor contrast should be run at `--effort medium`.

## Tests

`uv run pytest` runs offline against a scripted vision backend and the synthetic drawing in `examples/`
(regenerate it with `uv run python examples/make_sample.py`). `tests/test_live.py` hits the real model
and skips without a key.

MIT.
