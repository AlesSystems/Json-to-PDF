from hashlib import sha256
from pathlib import Path

import pytest

from json_to_pdf.errors import UnsupportedCharacterError
from json_to_pdf.font import register_bundled_font, require_supported_text

FONT = Path("src/json_to_pdf/assets/fonts/NotoSans[wdth,wght].ttf")
OFL = Path("src/json_to_pdf/assets/fonts/OFL.txt")


def test_font_assets_are_exact() -> None:
    assert sha256(FONT.read_bytes()).hexdigest() == (
        "bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d"
    )
    assert sha256(OFL.read_bytes()).hexdigest() == (
        "cee9892f9f0cc8fe882c9e9537ee6a89621d86ee7ceaf70b02e2b2b1c25c061a"
    )


def test_turkish_glyphs_are_supported(qapp) -> None:
    assert register_bundled_font() == "Noto Sans"
    require_supported_text(["ÇĞİÖŞÜçğıöşü"])


def test_unsupported_character_is_rejected(qapp) -> None:
    register_bundled_font()
    with pytest.raises(UnsupportedCharacterError, match="U\\+"):
        require_supported_text(["\U0001F9EA"])
