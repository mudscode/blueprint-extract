"""What the model returns for one page, and what the tool returns for a document.

PageExtraction is sent to the model as a strict JSON schema, so every field is required
(Optional means nullable, not omittable) and nothing has a default."""

from typing import Literal

from pydantic import BaseModel, Field

PageType = Literal["floor_plan", "elevation", "section", "site_plan", "detail", "schedule", "title", "other"]


class Room(BaseModel):
    name: str = Field(description="Label as drawn, e.g. 'BED 1', 'KITCHEN', 'LIVING'.")
    dimensions: str | None = Field(
        description="As written on the drawing, e.g. '3.6 x 3.6' or '3600 x 3600'. null if not shown."
    )
    area_sqm: float | None = Field(
        description="Square metres: the printed value, else the product of two stated metric dimensions, else null."
    )


class Openings(BaseModel):
    count: int = Field(ge=0, description="How many are drawn on this page. Count only what is visible.")
    types: list[str] = Field(description="Kinds seen, lowercase: 'entry', 'internal', 'sliding', 'casement'.")


class PageExtraction(BaseModel):
    page_type: PageType
    project: str | None = Field(description="Project name or site address from the title block. null if none.")
    title: str | None = Field(description="Sheet title, e.g. 'GROUND FLOOR PLAN', 'FRONT ELEVATION'. null if none.")
    scale: str | None = Field(description="Scale as written, e.g. '1:100'. null if none.")
    rooms: list[Room] = Field(description="Only on floor plans. Empty on every other page type.")
    doors: Openings
    windows: Openings
    fixtures: list[str] = Field(
        description="Fixed items drawn, lowercase: 'toilet', 'basin', 'kitchen bench', 'wardrobe'."
    )
    materials: list[str] = Field(
        description="Materials and finishes named on the page, lowercase: 'brick veneer', 'colorbond roof'."
    )
    text_labels: list[str] = Field(description="Other legible text worth keeping: dimensions, legend entries.")
    notes: list[str] = Field(description="Instructions: 'existing wall to be removed', 'new slab'.")
    confidence: float = Field(ge=0, le=1, description="How legible and complete this page was.")


class PageResult(BaseModel):
    page: int
    ok: bool
    data: PageExtraction | None = None
    error: str | None = None
    tokens: int = 0


class RoomSummary(BaseModel):
    count: int
    total_area_sqm: float
    by_type: dict[str, int]
    rooms: list[Room]


class OpeningSummary(BaseModel):
    count: int
    types: list[str]


class ProjectData(BaseModel):
    source: str
    project: str | None
    scales: list[str]
    pages_by_type: dict[str, list[int]]
    rooms: RoomSummary
    doors: OpeningSummary
    windows: OpeningSummary
    fixtures: list[str]
    materials: list[str]
    notes: list[str]
    pages: list[PageResult]
    failed_pages: list[int]
