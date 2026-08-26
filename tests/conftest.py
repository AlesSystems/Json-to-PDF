from datetime import date

import pytest

from json_to_pdf.pdf import PdfMetadata


@pytest.fixture(scope="session")
def registered_font(qapp):
    from json_to_pdf.font import FONT_FAMILY, register_bundled_font

    register_bundled_font()
    return FONT_FAMILY


@pytest.fixture
def metadata() -> PdfMetadata:
    return PdfMetadata("Title", "source.json", date(2026, 8, 26))


@pytest.fixture
def valid_html() -> str:
    return (
        "<h1>Title</h1>"
        "<p>Source: source.json</p>"
        "<p>Başarılı</p>"
        "<p>https://example.invalid/path</p>"
        "<p>&lt;a href=&quot;https://example.invalid&quot;&gt;link&lt;/a&gt;</p>"
    )
