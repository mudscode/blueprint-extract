"""One page image in, one PageExtraction out. OpenAI Responses API with structured output."""

import asyncio
import base64
import os
from typing import Any, Protocol

from .schema import PageExtraction

SYSTEM = """You read architectural drawings and fill in a fixed JSON schema for one page at a time.

Rules:
- Report only what is legible. Never guess dimensions or counts. When unsure of a count, give the
  lower number you are certain of.
- rooms: only on floor plans, one entry per labelled space, name exactly as drawn. On any other page
  type, rooms is an empty list.
- area_sqm: the printed area if there is one; otherwise the product of two stated metric dimensions
  (treat values over 100 as millimetres); otherwise null.
- doors and windows: count the symbols drawn on this page. A door is an arc or a leaf in a wall gap; a
  window is a thin double line in an external wall.
- fixtures and materials: lowercase, short, no duplicates.
- notes: instructions and annotations, not dimensions.
- project: the project name or site address from the title block, if any.
- page_type: floor_plan, elevation, section, site_plan, detail, schedule (tables of doors, windows,
  finishes), title (cover sheet), or other.
- confidence: how legible and complete the page was, 0 to 1."""


class VisionError(RuntimeError):
    """The model did not return usable structured output."""


class Vision(Protocol):
    async def describe(self, png: bytes, page: int) -> tuple[PageExtraction, int]:
        """Return (extraction, tokens_used) for one rendered page."""
        ...


def _uses_reasoning(model: str) -> bool:
    return model.startswith(("gpt-5", "o1", "o3", "o4"))


class OpenAIVision:
    def __init__(self, model: str | None = None, client: Any = None, effort: str = "low", retries: int = 2):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.effort = effort
        self.retries = retries
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:  # lazy so importing never needs a key
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI()
        return self._client

    def _request(self, png: bytes, page: int) -> dict:
        b64 = base64.standard_b64encode(png).decode()
        req: dict = {
            "model": self.model,
            "instructions": SYSTEM,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_image", "image_url": f"data:image/png;base64,{b64}", "detail": "high"},
                        {"type": "input_text", "text": f"This is page {page} of a drawing set. Extract it."},
                    ],
                }
            ],
            "text_format": PageExtraction,
        }
        if _uses_reasoning(self.model):
            req["reasoning"] = {"effort": self.effort}
        return req

    async def describe(self, png: bytes, page: int) -> tuple[PageExtraction, int]:
        req = self._request(png, page)
        last: BaseException | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = await self.client.responses.parse(**req)
            except Exception as e:  # network, rate limit, 5xx: worth retrying
                last = e
                if attempt < self.retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                continue
            if resp.output_parsed is None:  # refusal or malformed output: retrying rarely helps
                raise VisionError(f"page {page}: model returned no structured output")
            usage = getattr(resp, "usage", None)
            tokens = int(getattr(usage, "total_tokens", 0) or 0)
            return resp.output_parsed, tokens
        raise VisionError(f"page {page}: {type(last).__name__}: {last}") from last
