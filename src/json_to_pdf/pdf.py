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

from .errors import RenderError, ResourceLimitError
from .font import FONT_FAMILY
from .limits import DEFAULT_LIMITS, ResourceLimits


@dataclass(frozen=True)
class PdfMetadata:
    title: str
    source_name: str
    generated_on: date


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
