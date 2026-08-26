import pytest


@pytest.fixture(scope="session")
def registered_font(qapp):
    from json_to_pdf.font import FONT_FAMILY, register_bundled_font

    register_bundled_font()
    return FONT_FAMILY
