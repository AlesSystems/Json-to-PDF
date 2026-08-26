import re
from datetime import date

import pytest
from PySide6.QtGui import QPainter
from PySide6.QtPrintSupport import QPrinter
from pypdf import PdfReader

from json_to_pdf.errors import RenderError, ResourceLimitError
from json_to_pdf.limits import ResourceLimits
from json_to_pdf.pdf import PdfMetadata, _paint_document
from json_to_pdf.render import RenderContext, render_html


METADATA = PdfMetadata("Title", "fixture.json", date(2026, 8, 26))


def _read(output):
    reader = PdfReader(output, strict=True)
    return reader, [page.extract_text() or "" for page in reader.pages]


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text)


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
    assert [
        f"Page {i} of {count}" in _normalized(page)
        for i, page in enumerate(text, 1)
    ] == [True] * count


def test_one_page_has_one_footer_and_a4_media_box(tmp_path, registered_font) -> None:
    output = tmp_path / "one.pdf"
    count = _paint_document("<p>ONLY-SENTINEL</p>", output, METADATA)
    reader, text = _read(output)
    assert count == len(reader.pages) == 1
    assert "ONLY-SENTINEL" in text[0]
    assert _normalized(text[0]).count("Page 1 of 1") == 1
    assert tuple(map(float, reader.pages[0].mediabox)) == (0.0, 0.0, 595.0, 842.0)
    fonts = reader.pages[0]["/Resources"]["/Font"].get_object().values()
    assert all("NotoSans" in font.get_object()["/BaseFont"] for font in fonts)


def test_footer_geometry_reserves_margin_gap_and_band(
    tmp_path, registered_font, monkeypatch
) -> None:
    footer_rects = []
    translations = []

    class GeometryPainter(QPainter):
        def translate(self, dx, dy):
            translations.append((float(dx), float(dy)))
            return super().translate(dx, dy)

        def drawText(self, rect, flags, text):
            if text.startswith("Page "):
                footer_rects.append(rect)
            return super().drawText(rect, flags, text)

    monkeypatch.setattr("json_to_pdf.pdf.QPainter", GeometryPainter)
    output = tmp_path / "geometry.pdf"
    token = "W" * 80
    _paint_document(
        "<p>" + token + "</p>" + "<p>geometry row</p>" * 100,
        output,
        METADATA,
    )
    reader, text = _read(output)
    footer = footer_rects[0]
    mm = 72 / 25.4
    paint_margin = 18 * mm
    assert tuple(map(float, reader.pages[0].mediabox)) == (0.0, 0.0, 595.0, 842.0)
    assert footer.left() == pytest.approx(paint_margin, abs=0.5)
    assert footer.right() == pytest.approx(595 - paint_margin, abs=0.5)
    assert footer.height() == pytest.approx(7 * mm)
    assert footer.bottom() == pytest.approx(842 - paint_margin, abs=0.5)
    body_origin = next((dx, dy) for dx, dy in translations if dx > 0 and dy > 0)
    assert body_origin[0] == pytest.approx(paint_margin, abs=0.5)
    assert body_origin[1] == pytest.approx(paint_margin, abs=0.5)
    body_height = -max(dy for _, dy in translations if dy < 0)
    body_bottom = body_origin[1] + body_height
    assert footer.top() - body_bottom == pytest.approx(3 * mm)
    token_lines = [line for line in text[0].splitlines() if set(line) == {"W"}]
    assert "".join(token_lines) == token
    assert len(token_lines) >= 2


def test_real_renderer_typography_paginates_with_footer(
    tmp_path, registered_font
) -> None:
    context = RenderContext("Rendered title", "rendered.json", METADATA.generated_on)
    html = render_html(
        {"turkish_text": "ÇĞİÖŞÜ " * 400},
        context,
    )
    assert "line-height: 135%" in html
    output = tmp_path / "rendered.pdf"
    count = _paint_document(html, output, METADATA)
    reader, text = _read(output)
    assert len(reader.pages) == count >= 2
    first_page = _normalized(text[0])
    assert "Rendered title" in first_page
    assert "rendered.json" in first_page
    assert f"Page {count} of {count}" in _normalized(text[-1])


@pytest.mark.parametrize(
    "fragment",
    [
        "<p>" + "W" * 80 + "</p>",
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


def test_last_page_continuation_does_not_append_footer_only_page(
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
