from pathlib import Path

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .errors import ConversionError
from .model import ConversionRequest
from .pdf import PdfValidationResult
from .service import convert


class ConversionWorker(QObject):
    finished = Signal(PdfValidationResult)
    failed = Signal(ConversionError)

    def __init__(self, request: ConversionRequest) -> None:
        super().__init__()
        self._request = request

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(convert(self._request))
        except ConversionError as error:
            self.failed.emit(error)
        except Exception as error:
            self.failed.emit(ConversionError(error))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("JSON to PDF")
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None
        self._destination: Path | None = None

        self.source_edit = QLineEdit()
        self.destination_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.source_browse_button = QPushButton("Browse…")
        self.destination_browse_button = QPushButton("Browse…")
        self.generate_button = QPushButton("Generate PDF")
        self.open_button = QPushButton("Open Result")
        self.status_label = QLabel("Ready.")
        self.source_label = QLabel("&Source JSON:")
        self.destination_label = QLabel("&Destination PDF:")
        self.title_label = QLabel("&Title (optional):")

        self.source_label.setBuddy(self.source_edit)
        self.destination_label.setBuddy(self.destination_edit)
        self.title_label.setBuddy(self.title_edit)
        self.source_edit.setAccessibleName("Source JSON file")
        self.destination_edit.setAccessibleName("Destination PDF file")
        self.title_edit.setAccessibleName("Report title")
        self.source_browse_button.setAccessibleName("Browse for source JSON file")
        self.destination_browse_button.setAccessibleName("Browse for destination PDF file")
        self.generate_button.setAccessibleName("Generate PDF")
        self.open_button.setAccessibleName("Open Result")
        self.status_label.setAccessibleName("Conversion status")
        self.open_button.setEnabled(False)

        form = QFormLayout()
        form.addRow(self.source_label, self._path_row(self.source_edit, self.source_browse_button))
        form.addRow(
            self.destination_label,
            self._path_row(self.destination_edit, self.destination_browse_button),
        )
        form.addRow(self.title_label, self.title_edit)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.generate_button)
        buttons.addWidget(self.open_button)
        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setTabOrder(self.source_edit, self.source_browse_button)
        self.setTabOrder(self.source_browse_button, self.destination_edit)
        self.setTabOrder(self.destination_edit, self.destination_browse_button)
        self.setTabOrder(self.destination_browse_button, self.title_edit)
        self.setTabOrder(self.title_edit, self.generate_button)
        self.setTabOrder(self.generate_button, self.open_button)

        self.source_browse_button.clicked.connect(self.browse_source)
        self.destination_browse_button.clicked.connect(self.browse_destination)
        self.generate_button.clicked.connect(self.generate)
        self.open_button.clicked.connect(self.open_result)

    @staticmethod
    def _path_row(edit: QLineEdit, button: QPushButton) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit)
        layout.addWidget(button)
        return row

    @Slot()
    def browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose JSON source", "", "JSON files (*.json)")
        if path:
            self.source_edit.setText(path)

    @Slot()
    def browse_destination(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Choose PDF destination", "", "PDF files (*.pdf)")
        if path:
            self.destination_edit.setText(path)

    @Slot()
    def generate(self) -> None:
        source = self.source_edit.text().strip()
        destination = self.destination_edit.text().strip()
        if not source or not destination:
            QMessageBox.warning(
                self,
                "Missing information",
                "Choose a JSON source file and PDF destination.",
            )
            return
        title = self.title_edit.text().strip() or None
        self.start_conversion(ConversionRequest(Path(source), Path(destination), title))

    def start_conversion(self, request: ConversionRequest) -> None:
        if self._thread is not None:
            return
        self._destination = request.destination
        self.generate_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.status_label.setText("Generating PDF…")
        thread = QThread(self)
        worker = ConversionWorker(request)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._conversion_succeeded)
        worker.failed.connect(self._conversion_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._thread_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(PdfValidationResult)
    def _conversion_succeeded(self, result: PdfValidationResult) -> None:
        self.generate_button.setEnabled(True)
        self.open_button.setEnabled(True)
        self.status_label.setText("PDF generated successfully.")

    @Slot(ConversionError)
    def _conversion_failed(self, error: ConversionError) -> None:
        self.generate_button.setEnabled(True)
        self.open_button.setEnabled(False)
        self.status_label.setText("Conversion failed.")
        QMessageBox.critical(
            self,
            "Could not generate PDF",
            f"{error.public_message} Check the input and try again.",
        )

    @Slot()
    def _thread_finished(self) -> None:
        self._worker = None
        self._thread = None

    @Slot()
    def open_result(self) -> None:
        if self._destination is None:
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._destination))):
            QMessageBox.warning(
                self,
                "Could not open PDF",
                "Open the PDF from its destination folder.",
            )
