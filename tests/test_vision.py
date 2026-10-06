import asyncio
from types import SimpleNamespace

import pytest

from blueprint_extract.schema import PageExtraction
from blueprint_extract.vision import OpenAIVision, VisionError
from tests.conftest import make_page


class FakeResponses:
    def __init__(self, script):
        self.script = list(script)  # each item: PageExtraction | None | Exception
        self.requests = []

    async def parse(self, **kw):
        self.requests.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(output_parsed=item, usage=SimpleNamespace(total_tokens=321))


def client_with(script):
    r = FakeResponses(script)
    return SimpleNamespace(responses=r), r


def test_request_shape_for_reasoning_model():
    client, r = client_with([make_page()])
    v = OpenAIVision(model="gpt-5-mini", client=client, effort="medium")
    data, tokens = asyncio.run(v.describe(b"\x89PNG fake", 3))
    assert isinstance(data, PageExtraction) and tokens == 321
    req = r.requests[0]
    assert req["model"] == "gpt-5-mini"
    assert req["reasoning"] == {"effort": "medium"}
    assert req["text_format"] is PageExtraction
    content = req["input"][0]["content"]
    assert content[0]["type"] == "input_image" and content[0]["image_url"].startswith("data:image/png;base64,")
    assert content[0]["detail"] == "high"
    assert "page 3" in content[1]["text"]


def test_no_reasoning_block_for_non_reasoning_model():
    client, r = client_with([make_page()])
    asyncio.run(OpenAIVision(model="gpt-4o", client=client).describe(b"x", 1))
    assert "reasoning" not in r.requests[0]


def test_model_defaults_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "some-model")
    assert OpenAIVision().model == "some-model"
    monkeypatch.delenv("OPENAI_MODEL")
    assert OpenAIVision().model == "gpt-5-mini"
    assert OpenAIVision(model="explicit").model == "explicit"


def test_no_parsed_output_is_an_error_and_not_retried():
    client, r = client_with([None, make_page()])
    with pytest.raises(VisionError, match="no structured output"):
        asyncio.run(OpenAIVision(model="m", client=client, retries=2).describe(b"x", 7))
    assert len(r.requests) == 1


def test_transient_failure_is_retried(monkeypatch):
    monkeypatch.setattr("blueprint_extract.vision.asyncio.sleep", _no_sleep)
    client, r = client_with([ConnectionError("blip"), make_page()])
    data, _ = asyncio.run(OpenAIVision(model="m", client=client, retries=2).describe(b"x", 1))
    assert data.page_type == "floor_plan" and len(r.requests) == 2


def test_retries_exhausted_wraps_last_error(monkeypatch):
    monkeypatch.setattr("blueprint_extract.vision.asyncio.sleep", _no_sleep)
    client, r = client_with([TimeoutError("a"), TimeoutError("b"), TimeoutError("c")])
    with pytest.raises(VisionError, match="TimeoutError: c") as ei:
        asyncio.run(OpenAIVision(model="m", client=client, retries=2).describe(b"x", 1))
    assert isinstance(ei.value.__cause__, TimeoutError) and len(r.requests) == 3


def test_schema_is_strict_compatible():
    """OpenAI strict mode needs every property required and no defaults; Optional stays nullable."""
    schema = PageExtraction.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"])
    for name, prop in schema["properties"].items():
        assert "default" not in prop, name
    room = schema["$defs"]["Room"]
    assert set(room["required"]) == set(room["properties"])


async def _no_sleep(_):
    return None
