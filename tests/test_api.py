import pytest
from fastapi.testclient import TestClient

from blueprint_extract import api
from tests.conftest import FakeVision, make_page


@pytest.fixture
def client():
    v = FakeVision({1: make_page(), 2: make_page("elevation")})
    api.app.dependency_overrides[api.get_vision] = lambda: v
    with TestClient(api.app) as c:
        c.vision = v  # type: ignore[attr-defined]
        yield c
    api.app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_extract_upload(client, sample_pdf):
    r = client.post("/extract", files={"file": ("plan.pdf", sample_pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "plan.pdf" and body["rooms"]["count"] == 5 and body["failed_pages"] == []


def test_extract_page_subset(client, sample_pdf):
    r = client.post("/extract?pages=2", files={"file": ("plan.pdf", sample_pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 200 and [p["page"] for p in r.json()["pages"]] == [2]
    assert client.vision.calls == [2]


def test_rejects_non_pdf_and_bad_pages(client, sample_pdf):
    r = client.post("/extract", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400 and r.json()["detail"] == "not a PDF"
    r = client.post("/extract?pages=5", files={"file": ("plan.pdf", sample_pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 400 and "1..2" in r.json()["detail"]
    r = client.post("/extract?max_side=10", files={"file": ("plan.pdf", sample_pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 422


def test_default_dependency_is_openai_vision():
    from blueprint_extract.vision import OpenAIVision

    assert isinstance(api.get_vision(), OpenAIVision)
