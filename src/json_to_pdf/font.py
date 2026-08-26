from collections.abc import Iterable
from importlib.resources import files
from unicodedata import category

from PySide6.QtGui import QFontDatabase, QRawFont

from .errors import UnsupportedCharacterError

FONT_FAMILY = "Noto Sans"
_raw_font: QRawFont | None = None


def register_bundled_font() -> str:
    global _raw_font
    _raw_font = None
    path = files("json_to_pdf").joinpath("assets/fonts/NotoSans[wdth,wght].ttf")
    font_id = QFontDatabase.addApplicationFont(str(path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if FONT_FAMILY not in families:
        raise RuntimeError("The bundled report font could not be loaded.")
    raw_font = QRawFont(str(path), 10.0)
    if not raw_font.isValid():
        raise RuntimeError("The bundled report font could not be loaded.")
    _raw_font = raw_font
    return FONT_FAMILY


def require_supported_text(texts: Iterable[str]) -> None:
    if _raw_font is None:
        raise RuntimeError("The bundled report font is not registered.")
    for char in set().union(*(set(text) for text in texts)):
        if char in "\n\r\t":
            continue
        if category(char) in {"Cc", "Cf"} or not _raw_font.supportsCharacter(
            ord(char)
        ):
            raise UnsupportedCharacterError(ord(char))
