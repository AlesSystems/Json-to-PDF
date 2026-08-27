from collections.abc import Iterable
from hashlib import sha256
from importlib.resources import files
from unicodedata import category

from PySide6.QtGui import QFontDatabase, QRawFont

from .errors import UnsupportedCharacterError

FONT_FAMILY = "Noto Sans"
FONT_SHA256 = "bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d"
_raw_font: QRawFont | None = None


def register_bundled_font() -> str:
    global _raw_font
    _raw_font = None
    path = files("json_to_pdf").joinpath("assets/fonts/NotoSans[wdth,wght].ttf")
    try:
        if sha256(path.read_bytes()).hexdigest() != FONT_SHA256:
            raise RuntimeError("The bundled report font could not be loaded.")
    except RuntimeError:
        raise
    except (OSError, TypeError) as error:
        raise RuntimeError("The bundled report font could not be loaded.") from error
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
