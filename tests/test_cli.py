import json

from blueprint_extract import cli
from tests.conftest import FakeVision, make_page


def test_dry_run_calls_no_model(sample_pdf, capsys, monkeypatch):
    monkeypatch.setattr(cli, "build_vision", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert cli.main([str(sample_pdf), "--dry-run", "--max-side", "500"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("page 1: 500x") and "page 2:" in out


def test_extract_to_stdout_and_summary(sample_pdf, capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    v = FakeVision({1: make_page(), 2: make_page("elevation")})
    monkeypatch.setattr(cli, "build_vision", lambda model, effort: v)
    assert cli.main([str(sample_pdf), "--summary"]) == 0
    cap = capsys.readouterr()
    data = json.loads(cap.out)
    assert data["rooms"]["count"] == 5 and data["source"] == "sample_plan.pdf"
    assert "2/2 pages extracted" in cap.err and "Rooms:    5" in cap.err


def test_extract_to_file_with_page_subset(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    v = FakeVision({1: make_page(), 2: make_page("elevation")})
    monkeypatch.setattr(cli, "build_vision", lambda model, effort: v)
    out = tmp_path / "out.json"
    assert cli.main([str(sample_pdf), "-o", str(out), "--pages", "2"]) == 0
    data = json.loads(out.read_text())
    assert [p["page"] for p in data["pages"]] == [2] and v.calls == [2]
    assert data["rooms"]["count"] == 0 and data["materials"] == ["brick veneer", "colorbond roof"]


def test_exit_codes(sample_pdf, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    assert cli.main([str(tmp_path / "missing.pdf")]) == 2
    assert cli.main([str(sample_pdf), "--pages", "9"]) == 2
    assert "outside" in capsys.readouterr().err
    v = FakeVision({1: RuntimeError("x"), 2: RuntimeError("y")})
    monkeypatch.setattr(cli, "build_vision", lambda model, effort: v)
    assert cli.main([str(sample_pdf)]) == 1
    err = capsys.readouterr().err
    assert "0/2 pages extracted" in err and "page 1: RuntimeError: x" in err


def test_model_and_effort_reach_the_factory(sample_pdf, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    seen = {}

    def factory(model, effort):
        seen.update(model=model, effort=effort)
        return FakeVision({1: make_page(), 2: make_page("elevation")})

    monkeypatch.setattr(cli, "build_vision", factory)
    assert cli.main([str(sample_pdf), "--model", "gpt-4o", "--effort", "high"]) == 0
    assert seen == {"model": "gpt-4o", "effort": "high"}


def test_missing_api_key_fails_fast(sample_pdf, capsys, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "build_vision", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert cli.main([str(sample_pdf)]) == 2
    assert "OPENAI_API_KEY" in capsys.readouterr().err
