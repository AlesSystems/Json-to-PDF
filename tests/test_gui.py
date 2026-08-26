from pathlib import Path
from threading import Event

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from json_to_pdf.errors import InputReadError
from json_to_pdf.gui import MainWindow
from json_to_pdf.model import ConversionRequest
from json_to_pdf.pdf import PdfValidationResult


def _request(tmp_path: Path) -> ConversionRequest:
    return ConversionRequest(tmp_path / "input.json", tmp_path / "output.pdf", "Report")


def _next_focusable(widget):
    candidate = widget.nextInFocusChain()
    while candidate.focusPolicy() == Qt.FocusPolicy.NoFocus:
        candidate = candidate.nextInFocusChain()
    return candidate


def test_form_is_labeled_and_keyboard_ordered(qtbot, registered_font) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.source_label.buddy() is window.source_edit
    assert window.destination_label.buddy() is window.destination_edit
    assert window.title_label.buddy() is window.title_edit
    assert window.generate_button.accessibleName() == "Generate PDF"
    assert _next_focusable(window.source_edit) is window.source_browse_button
    assert _next_focusable(window.source_browse_button) is window.destination_edit
    assert _next_focusable(window.destination_edit) is window.destination_browse_button
    assert _next_focusable(window.destination_browse_button) is window.title_edit
    assert _next_focusable(window.title_edit) is window.generate_button
    assert _next_focusable(window.generate_button) is window.open_button
    assert not window.open_button.isEnabled()


def test_conversion_runs_off_the_gui_thread_and_cleans_up(
    qtbot, registered_font, monkeypatch, tmp_path
) -> None:
    release = Event()
    worker_thread: list[QThread] = []

    def blocking_convert(request: ConversionRequest) -> PdfValidationResult:
        worker_thread.append(QThread.currentThread())
        release.wait(2)
        return PdfValidationResult(1, ("Report",))

    monkeypatch.setattr("json_to_pdf.gui.convert", blocking_convert)
    window = MainWindow()
    qtbot.addWidget(window)
    window.start_conversion(_request(tmp_path))

    assert window.status_label.text() == "Generating PDF…"
    assert not window.generate_button.isEnabled()
    assert worker_thread == []
    release.set()
    qtbot.waitUntil(window.open_button.isEnabled)
    qtbot.waitUntil(lambda: window._thread is None)

    assert worker_thread[0] is not QThread.currentThread()
    assert window.generate_button.isEnabled()
    assert window.status_label.text() == "PDF generated successfully."


def test_failure_is_redacted_actionable_and_restores_controls(
    qtbot, registered_font, monkeypatch, tmp_path
) -> None:
    messages: list[tuple[str, str]] = []

    def fail(request: ConversionRequest) -> PdfValidationResult:
        raise InputReadError(ValueError("/secret/path secret-value"))

    monkeypatch.setattr("json_to_pdf.gui.convert", fail)
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, text: messages.append((title, text)),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.start_conversion(_request(tmp_path))
    qtbot.waitUntil(lambda: window._thread is None)

    assert window.generate_button.isEnabled()
    assert not window.open_button.isEnabled()
    assert window.status_label.text() == "Conversion failed."
    assert messages == [
        ("Could not generate PDF", "The JSON file could not be read. Check the input and try again."),
    ]
    assert "/secret/path" not in repr(messages)
    assert "secret-value" not in repr(messages)


def test_required_fields_are_validated_without_starting_work(
    qtbot, registered_font, monkeypatch
) -> None:
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, text: messages.append((title, text)),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.generate()

    assert window._thread is None
    assert messages == [("Missing information", "Choose a JSON source file and PDF destination.")]


def test_open_result_uses_local_file_url(qtbot, registered_font, monkeypatch, tmp_path) -> None:
    opened: list[QUrl] = []
    destination = tmp_path / "output file.pdf"
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url) or True)
    window = MainWindow()
    qtbot.addWidget(window)
    window._destination = destination
    window.open_button.setEnabled(True)

    window.open_result()

    assert opened == [QUrl.fromLocalFile(str(destination))]


def test_open_failure_warns_without_changing_conversion_success(
    qtbot, registered_font, monkeypatch, tmp_path
) -> None:
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: False)
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda parent, title, text: messages.append((title, text)),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window._destination = tmp_path / "output.pdf"
    window.open_button.setEnabled(True)
    window.status_label.setText("PDF generated successfully.")

    window.open_result()

    assert window.status_label.text() == "PDF generated successfully."
    assert window.open_button.isEnabled()
    assert messages == [("Could not open PDF", "Open the PDF from its destination folder.")]
