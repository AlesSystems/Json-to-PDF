import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .errors import ConversionError
from .font import register_bundled_font
from .gui import MainWindow
from .model import ConversionRequest
from .service import convert


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(arguments)
    register_bundled_font()
    if len(arguments) == 4 and arguments[1] == "--smoke-convert":
        try:
            convert(ConversionRequest(Path(arguments[2]), Path(arguments[3])))
        except ConversionError:
            return 1
        return 0
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
