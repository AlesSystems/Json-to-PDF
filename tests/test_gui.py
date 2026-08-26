from pathlib import Path
from threading import Event

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget

from json_to_pdf.errors import InputReadError, OutputWriteError
from json_to_pdf.gui import MainWindow
from json_to_pdf.model import ConversionRequest
from json_to_pdf.pdf import PdfValidationResult


def test_main_window_honors_parent_ownership(qtbot, registered_font) -> None:
    parent = QWidget()
    window = MainWindow(parent)
    qtbot.addWidget(parent)

    assert window.parent() is parent


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


def test_window_refuses_close_until_active_conversion_finishes(
    qtbot, registered_font, monkeypatch, tmp_path
) -> None:
    release = Event()

    def blocking_convert(request: ConversionRequest) -> PdfValidationResult:
        release.wait(2)
        return PdfValidationResult(1, ("Report",))

    monkeypatch.setattr("json_to_pdf.gui.convert", blocking_convert)
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.start_conversion(_request(tmp_path))

    close_result = window.close()
    remained_visible = window.isVisible()
    release.set()
    qtbot.waitUntil(lambda: window._thread is None)
    assert not close_result
    assert remained_visible
    assert window.close()


def test_generate_stays_disabled_until_thread_cleanup_boundary(
    qtbot, registered_font, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "json_to_pdf.gui.convert",
        lambda request: PdfValidationResult(1, ("Second report",)),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.generate_button.setEnabled(False)
    window._thread = QThread(window)

    window._conversion_succeeded(PdfValidationResult(1, ("Report",)))

    assert not window.generate_button.isEnabled()
    window._thread_finished()
    assert window.generate_button.isEnabled()
    window.start_conversion(_request(tmp_path))
    qtbot.waitUntil(lambda: window._thread is None)
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


def test_output_failure_advises_a_writable_destination(
    qtbot, registered_font, monkeypatch, tmp_path
) -> None:
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "json_to_pdf.gui.convert",
        lambda request: (_ for _ in ()).throw(
            OutputWriteError(ValueError("/secret/path secret-value"))
        ),
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, text: messages.append((title, text)),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.start_conversion(_request(tmp_path))
    qtbot.waitUntil(lambda: window._thread is None)

    assert messages == [
        (
            "Could not generate PDF",
            "The PDF file could not be written. Choose a writable PDF destination and try again.",
        )
    ]
    assert "/secret/path" not in repr(messages)
    assert "secret-value" not in repr(messages)


def test_unexpected_worker_exception_is_redacted_and_cleans_up(
    qtbot, registered_font, monkeypatch, tmp_path
) -> None:
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "json_to_pdf.gui.convert",
        lambda request: (_ for _ in ()).throw(
            RuntimeError("/secret/path secret-value")
        ),
    )
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
    assert messages == [
        (
            "Could not generate PDF",
            "The conversion could not be completed. Check the input and try again.",
        )
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
