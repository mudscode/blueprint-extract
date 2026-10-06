"""Architectural drawing PDFs to structured JSON with a vision model."""

from .pipeline import extract, extract_sync
from .schema import PageExtraction, ProjectData
from .vision import OpenAIVision, Vision, VisionError

__version__ = "0.1.0"
__all__ = ["OpenAIVision", "PageExtraction", "ProjectData", "Vision", "VisionError", "extract", "extract_sync"]
