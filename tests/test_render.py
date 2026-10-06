import pytest

from blueprint_extract.render import page_count, parse_pages, render_pages

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_page_count(sample_pdf):
    assert page_count(sample_pdf) == 2
    assert page_count(sample_pdf.read_bytes()) == 2


def test_render_all_pages_fit_max_side(sample_pdf):
    pages = render_pages(sample_pdf, max_side=1000)
    assert [p.number for p in pages] == [1, 2]
    for p in pages:
        assert p.png.startswith(PNG_MAGIC)
        assert max(p.width, p.height) == 1000
        assert min(p.width, p.height) > 0


def test_render_subset_and_bytes_input(sample_pdf):
    pages = render_pages(sample_pdf.read_bytes(), pages=[2, 2, 1], max_side=400)
    assert [p.number for p in pages] == [1, 2]  # de-duplicated and sorted


def test_render_out_of_range(sample_pdf):
    with pytest.raises(ValueError, match="out of range"):
        render_pages(sample_pdf, pages=[3])
    with pytest.raises(ValueError, match="max_side"):
        render_pages(sample_pdf, max_side=10)


@pytest.mark.parametrize(
    "spec,expected",
    [
        ("1", [1]),
        ("1-3", [1, 2, 3]),
        ("1-3,5", [1, 2, 3, 5]),
        ("8-", [8, 9, 10]),
        ("-2", [1, 2]),
        (" 3 , 1 ", [1, 3]),
        ("2,2,2", [2]),
    ],
)
def test_parse_pages(spec, expected):
    assert parse_pages(spec, 10) == expected


@pytest.mark.parametrize("spec", ["0", "11", "5-3", "1-11", "", ",", "a"])
def test_parse_pages_rejects(spec):
    with pytest.raises(ValueError):
        parse_pages(spec, 10)
