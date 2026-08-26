import os
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import (
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QTextDocument,
    QTextOption,
)
from PySide6.QtPrintSupport import QPrinter
from pypdf import PdfReader

from .errors import (
    ConversionError,
    OutputWriteError,
    PdfValidationError,
    RenderError,
    ResourceLimitError,
)
from .font import FONT_FAMILY
from .limits import DEFAULT_LIMITS, ResourceLimits


@dataclass(frozen=True)
class PdfMetadata:
    title: str
    source_name: str
    generated_on: date


@dataclass(frozen=True)
class PdfValidationResult:
    page_count: int
    extracted_text: tuple[str, ...]


def _searchable_metadata(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def validate_pdf(
    path: Path,
    *,
    expected_title: str,
    expected_source_name: str,
    limits: ResourceLimits = DEFAULT_LIMITS,
) -> PdfValidationResult:
    try:
        if path.stat().st_size > limits.max_pdf_bytes:
            raise PdfValidationError()
        with path.open("rb") as stream:
            reader = PdfReader(stream, strict=True)
            if reader.is_encrypted or not 1 <= len(reader.pages) <= limits.max_pages:
                raise PdfValidationError()
            texts = tuple(page.extract_text() or "" for page in reader.pages)
            if any(not text.strip() for text in texts):
                raise PdfValidationError()
            combined = _searchable_metadata("\n".join(texts))
            if (
                _searchable_metadata(expected_title) not in combined
                or _searchable_metadata(expected_source_name) not in combined
            ):
                raise PdfValidationError()
    except PdfValidationError:
        raise
    except Exception as error:
        raise PdfValidationError(cause=error) from error
    return PdfValidationResult(len(texts), texts)


def write_pdf_atomic(
    html_text: str,
    destination: Path,
    metadata: PdfMetadata,
    limits: ResourceLimits = DEFAULT_LIMITS,
) -> PdfValidationResult:
    temp = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp.pdf",
            dir=destination.parent,
        )
        temp = Path(temp_name)
        try:
            os.close(fd)
        except OSError:
            os.close(fd)
            raise
    except OSError as error:
        if temp is not None:
            _unlink_temp(temp)
        raise OutputWriteError(cause=error) from error
    try:
        _paint_document(html_text, temp, metadata, limits)
        result = validate_pdf(
            temp,
            expected_title=metadata.title,
            expected_source_name=metadata.source_name,
            limits=limits,
        )
        os.replace(temp, destination)
        return result
    except ConversionError:
        raise
    except OSError as error:
        raise OutputWriteError(cause=error) from error
    finally:
        _unlink_temp(temp)


def _unlink_temp(temp: Path) -> None:
    if not temp.exists():
        return
    try:
        temp.unlink()
    except OSError as error:
        try:
            temp.unlink()
        except OSError:
            raise OutputWriteError(cause=error) from error


def _paint_document(
    html_text: str,
    output: Path,
    metadata: PdfMetadata,
    limits: ResourceLimits = DEFAULT_LIMITS,
) -> int:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setResolution(72)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output))
    layout = QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Portrait,
        QMarginsF(18, 18, 18, 18),
        QPageLayout.Unit.Millimeter,
    )
    if not printer.setPageLayout(layout):
        raise RenderError()

    paint = printer.pageLayout().paintRectPixels(printer.resolution())
    mm = printer.resolution() / 25.4
    footer_height, footer_gap = 7 * mm, 3 * mm
    body = QRectF(
        paint.left(),
        paint.top(),
        paint.width(),
        paint.height() - footer_height - footer_gap,
    )
    footer = QRectF(
        paint.left(), body.bottom() + footer_gap, paint.width(), footer_height
    )

    document = QTextDocument()
    document.setDefaultFont(QFont(FONT_FAMILY, 10))
    option = document.defaultTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    document.setDefaultTextOption(option)
    document.setDocumentMargin(0)
    document.setHtml(html_text)
    document.documentLayout().setPaintDevice(printer)
    document.setPageSize(body.size())
    document.documentLayout().documentSize()
    pages = document.pageCount()
    if not 1 <= pages <= limits.max_pages:
        raise ResourceLimitError()

    painter = QPainter()
    if not painter.begin(printer):
        raise RenderError()
    painter.setFont(QFont(FONT_FAMILY, 10))
    for index in range(pages):
        painter.save()
        painter.translate(body.left(), body.top())
        context = document.documentLayout().PaintContext()
        context.clip = QRectF(
            0, index * body.height(), body.width(), body.height()
        )
        painter.translate(0, -index * body.height())
        document.documentLayout().draw(painter, context)
        painter.restore()
        painter.drawText(
            footer,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"Page {index + 1} of {pages}",
        )
        if index + 1 < pages and not printer.newPage():
            if not painter.end():
                raise RenderError()
            raise RenderError()
    if not painter.end():
        raise RenderError()
    return pages
