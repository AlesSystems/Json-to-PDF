from datetime import date

import pytest
from PySide6.QtGui import QPainter
from PySide6.QtPrintSupport import QPrinter
from pypdf import PdfReader

from json_to_pdf.errors import RenderError, ResourceLimitError
from json_to_pdf.limits import ResourceLimits
from json_to_pdf.pdf import PdfMetadata, _paint_document


METADATA = PdfMetadata("Title", "fixture.json", date(2026, 8, 26))


def _read(output):
    reader = PdfReader(output, strict=True)
    return reader, [page.extract_text() or "" for page in reader.pages]


def test_footer_pagination_has_no_extra_page(tmp_path, registered_font) -> None:
    html = (
        "<h1>FIRST-SENTINEL</h1>"
        + "<p>Long Turkish text ÇĞİÖŞÜ.</p>" * 700
        + "<p>LAST-SENTINEL</p>"
    )
    output = tmp_path / "pages.pdf"
    count = _paint_document(html, output, METADATA)
    reader, text = _read(output)
    assert len(reader.pages) == count >= 2
    assert "FIRST-SENTINEL" in text[0]
    assert "LAST-SENTINEL" in text[-1]
    assert [f"Page {i} of {count}" in page for i, page in enumerate(text, 1)] == [
        True
    ] * count


def test_one_page_has_one_footer_and_a4_media_box(tmp_path, registered_font) -> None:
    output = tmp_path / "one.pdf"
    count = _paint_document("<p>ONLY-SENTINEL</p>", output, METADATA)
    reader, text = _read(output)
    assert count == len(reader.pages) == 1
    assert "ONLY-SENTINEL" in text[0]
    assert text[0].count("Page 1 of 1") == 1
    assert tuple(map(float, reader.pages[0].mediabox)) == (0.0, 0.0, 595.0, 842.0)


@pytest.mark.parametrize(
    "fragment",
    [
        "<p>" + "X" * 80 + "</p>",
        "<table><tr><th>A</th><th>B</th><th>C</th><th>D</th></tr>"
        "<tr><td>alpha</td><td>beta</td><td>gamma</td><td>delta</td></tr></table>",
        '<div class="record-card"><h2>Record 1</h2><p>card value</p></div>',
        "<p>Çok uzun Türkçe anlatım: çğıöşü İstanbul.</p>" * 120,
    ],
    ids=["unbroken-token", "four-column-table", "record-card", "turkish-prose"],
)
def test_adversarial_content_reaches_last_page_without_blank_page(
    tmp_path, registered_font, fragment
) -> None:
    output = tmp_path / "adversarial.pdf"
    count = _paint_document(
        "<p>FIRST-EDGE</p>" + fragment + "<p>LAST-EDGE</p>", output, METADATA
    )
    reader, text = _read(output)
    assert len(reader.pages) == count
    assert all(page.strip() for page in text)
    assert "FIRST-EDGE" in text[0]
    assert "LAST-EDGE" in text[-1]


def test_exact_last_page_boundary_does_not_append_blank_page(
    tmp_path, registered_font
) -> None:
    output = tmp_path / "boundary.pdf"
    html = (
        "<p>FIRST-BOUNDARY</p>"
        + "<p>boundary row</p>" * 61
        + "<p>LAST-BOUNDARY</p>"
    )
    count = _paint_document(html, output, METADATA)
    reader, text = _read(output)
    assert len(reader.pages) == count
    assert "LAST-BOUNDARY" in text[-1]
    assert text[-1].strip() != f"Page {count} of {count}"


def test_rejects_document_over_page_limit(tmp_path, registered_font) -> None:
    with pytest.raises(ResourceLimitError):
        _paint_document(
            "<p>too many pages</p>" * 100,
            tmp_path / "limited.pdf",
            METADATA,
            ResourceLimits(max_pages=1),
        )


def test_rejects_painter_begin_failure(tmp_path, registered_font, monkeypatch) -> None:
    class BeginFailure(QPainter):
        def begin(self, device) -> bool:
            return False

    monkeypatch.setattr("json_to_pdf.pdf.QPainter", BeginFailure)
    with pytest.raises(RenderError):
        _paint_document("<p>content</p>", tmp_path / "begin.pdf", METADATA)


def test_rejects_painter_end_failure(tmp_path, registered_font, monkeypatch) -> None:
    class EndFailure(QPainter):
        def end(self) -> bool:
            super().end()
            return False

    monkeypatch.setattr("json_to_pdf.pdf.QPainter", EndFailure)
    with pytest.raises(RenderError):
        _paint_document("<p>content</p>", tmp_path / "end.pdf", METADATA)


def test_rejects_new_page_failure(tmp_path, registered_font, monkeypatch) -> None:
    class NewPageFailure(QPrinter):
        def newPage(self) -> bool:
            return False

    monkeypatch.setattr("json_to_pdf.pdf.QPrinter", NewPageFailure)
    with pytest.raises(RenderError):
        _paint_document(
            "<p>content</p>" * 100, tmp_path / "new-page.pdf", METADATA
        )
