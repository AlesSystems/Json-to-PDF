from pathlib import Path

from json_to_pdf.errors import InputReadError
from json_to_pdf.model import ConversionRequest
from json_to_pdf.pdf import PdfValidationResult


def test_smoke_conversion_registers_font_and_uses_service(monkeypatch, tmp_path) -> None:
    from json_to_pdf import __main__

    events: list[object] = []
    source = tmp_path / "input.json"
    destination = tmp_path / "output.pdf"
    monkeypatch.setattr(__main__, "register_bundled_font", lambda: events.append("font"))
    monkeypatch.setattr(
        __main__,
        "convert",
        lambda request: events.extend(("convert", request)) or PdfValidationResult(1, ("ok",)),
    )

    assert __main__.main(["json-to-pdf", "--smoke-convert", str(source), str(destination)]) == 0
    assert events == ["font", "convert", ConversionRequest(source, destination)]


def test_smoke_conversion_returns_one_for_typed_failure(monkeypatch, tmp_path) -> None:
    from json_to_pdf import __main__

    monkeypatch.setattr(__main__, "register_bundled_font", lambda: None)
    monkeypatch.setattr(__main__, "convert", lambda request: (_ for _ in ()).throw(InputReadError()))

    assert __main__.main(
        ["json-to-pdf", "--smoke-convert", str(tmp_path / "missing.json"), str(tmp_path / "out.pdf")]
    ) == 1


def test_gui_path_registers_font_and_shows_window(monkeypatch) -> None:
    from json_to_pdf import __main__

    events: list[str] = []

    class ApplicationSpy:
        @staticmethod
        def instance():
            return None

        def __init__(self, argv) -> None:
            events.append("application")

        def exec(self) -> int:
            events.append("exec")
            return 7

    class WindowSpy:
        def __init__(self) -> None:
            events.append("window")

        def show(self) -> None:
            events.append("show")

    monkeypatch.setattr(__main__, "QApplication", ApplicationSpy)
    monkeypatch.setattr(__main__, "MainWindow", WindowSpy)
    monkeypatch.setattr(__main__, "register_bundled_font", lambda: events.append("font"))

    assert __main__.main(["json-to-pdf"]) == 7
    assert events == ["application", "font", "window", "show", "exec"]
