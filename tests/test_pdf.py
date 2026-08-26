import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSize
from PySide6.QtPdf import QPdfDocument
from pypdf import PdfWriter

from json_to_pdf.errors import OutputWriteError, PdfValidationError, RenderError
from json_to_pdf.limits import ResourceLimits
from json_to_pdf.pdf import validate_pdf, write_pdf_atomic


def test_atomic_failure_preserves_destination(
    tmp_path, valid_html, metadata, registered_font, monkeypatch
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")

    def fail_validation(*args, **kwargs):
        raise PdfValidationError()

    monkeypatch.setattr("json_to_pdf.pdf.validate_pdf", fail_validation)
    with pytest.raises(PdfValidationError):
        write_pdf_atomic(valid_html, destination, metadata)
    assert destination.read_bytes() == b"prior-pdf"
    assert list(tmp_path.glob(".*.tmp.pdf")) == []


def test_success_replaces_destination_with_valid_searchable_pdf(
    tmp_path, valid_html, metadata, registered_font
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")
    result = write_pdf_atomic(valid_html, destination, metadata)
    assert result.page_count == 1
    assert "Title" in result.extracted_text[0]
    assert "source.json" in result.extracted_text[0]
    assert "Başarılı" in result.extracted_text[0]
    assert destination.read_bytes().startswith(b"%PDF")
    assert list(tmp_path.glob(".*.tmp.pdf")) == []


def test_validation_stream_is_closed_before_replacement(
    tmp_path, valid_html, metadata, monkeypatch
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")
    observed_streams = []

    class Page:
        def extract_text(self):
            return "Title source.json"

    class Reader:
        is_encrypted = False
        pages = [Page()]

        def __init__(self, stream, *, strict):
            assert strict is True
            observed_streams.append(stream)

    def paint_stub(html_text, output, metadata, limits):
        output.write_bytes(b"temporary")
        return 1

    real_replace = os.replace

    def replace_after_close(source, target):
        assert observed_streams and observed_streams[0].closed
        real_replace(source, target)

    monkeypatch.setattr("json_to_pdf.pdf.PdfReader", Reader)
    monkeypatch.setattr("json_to_pdf.pdf._paint_document", paint_stub)
    monkeypatch.setattr("json_to_pdf.pdf.os.replace", replace_after_close)
    write_pdf_atomic(valid_html, destination, metadata)
    assert destination.read_bytes() == b"temporary"


def test_strict_validation_rejects_corrupt_pdf(tmp_path) -> None:
    corrupt = tmp_path / "bad.pdf"
    corrupt.write_bytes(b"%PDF-1.7\ncorrupt")
    with pytest.raises(PdfValidationError):
        validate_pdf(
            corrupt,
            expected_title="Title",
            expected_source_name="source.json",
        )


def _write_pages(path: Path, count: int, *, password: str | None = None) -> None:
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=595, height=842)
    if password:
        writer.encrypt(password)
    with path.open("wb") as stream:
        writer.write(stream)


def test_strict_validation_rejects_blank_pdf(tmp_path) -> None:
    blank = tmp_path / "blank.pdf"
    _write_pages(blank, 1)
    with pytest.raises(PdfValidationError):
        validate_pdf(blank, expected_title="Title", expected_source_name="source.json")


def test_strict_validation_rejects_encrypted_pdf(tmp_path) -> None:
    encrypted = tmp_path / "encrypted.pdf"
    _write_pages(encrypted, 1, password="secret-value")
    with pytest.raises(PdfValidationError):
        validate_pdf(
            encrypted, expected_title="Title", expected_source_name="source.json"
        )


def test_strict_validation_rejects_oversized_pdf(tmp_path) -> None:
    oversized = tmp_path / "oversized.pdf"
    oversized.write_bytes(b"%PDF" * 20)
    with pytest.raises(PdfValidationError):
        validate_pdf(
            oversized,
            expected_title="Title",
            expected_source_name="source.json",
            limits=ResourceLimits(max_pdf_bytes=16),
        )


def test_strict_validation_rejects_too_many_pages(tmp_path) -> None:
    many = tmp_path / "many.pdf"
    _write_pages(many, 2)
    with pytest.raises(PdfValidationError):
        validate_pdf(
            many,
            expected_title="Title",
            expected_source_name="source.json",
            limits=ResourceLimits(max_pages=1),
        )


def test_validation_error_redacts_path_and_reader_detail(tmp_path) -> None:
    secret = "PRIVATE-reader-sentinel"
    path = tmp_path / secret
    path.write_bytes(b"not a pdf")
    with pytest.raises(PdfValidationError) as caught:
        validate_pdf(path, expected_title="Title", expected_source_name="source.json")
    assert secret not in str(caught.value)
    assert caught.value.public_message == "The generated PDF is invalid."


def test_painter_failure_preserves_destination_and_cleans_temp(
    tmp_path, valid_html, metadata, monkeypatch
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")

    def fail_paint(*args, **kwargs):
        raise RenderError()

    monkeypatch.setattr("json_to_pdf.pdf._paint_document", fail_paint)
    with pytest.raises(RenderError):
        write_pdf_atomic(valid_html, destination, metadata)
    assert destination.read_bytes() == b"prior-pdf"
    assert list(tmp_path.glob(".*.tmp.pdf")) == []


def test_replacement_failure_preserves_destination_and_cleans_temp(
    tmp_path, valid_html, metadata, registered_font, monkeypatch
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")

    monkeypatch.setattr(
        "json_to_pdf.pdf.validate_pdf", lambda *args, **kwargs: object()
    )

    def fail_replace(*args, **kwargs):
        raise OSError("PRIVATE-replace-sentinel")

    monkeypatch.setattr("json_to_pdf.pdf.os.replace", fail_replace)
    with pytest.raises(OutputWriteError) as caught:
        write_pdf_atomic(valid_html, destination, metadata)
    assert "PRIVATE-replace-sentinel" not in str(caught.value)
    assert destination.read_bytes() == b"prior-pdf"
    assert list(tmp_path.glob(".*.tmp.pdf")) == []


def test_generated_pdf_embeds_font_has_no_annotations_and_rasterizes_nonblank(
    tmp_path, valid_html, metadata, registered_font
) -> None:
    destination = tmp_path / "quality.pdf"
    result = write_pdf_atomic(valid_html, destination, metadata)

    from pypdf import PdfReader

    reader = PdfReader(destination, strict=True)
    embedded = False
    for page in reader.pages:
        annotations = page.get("/Annots")
        assert annotations is None or not annotations.get_object()
        fonts = page["/Resources"]["/Font"].get_object().values()
        for font_reference in fonts:
            font = font_reference.get_object()
            descendants = font.get("/DescendantFonts", [])
            descriptor = font.get("/FontDescriptor")
            if descendants:
                descriptor = descendants[0].get_object().get("/FontDescriptor")
            if descriptor:
                descriptor = descriptor.get_object()
                embedded |= any(
                    key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")
                )
    assert embedded

    document = QPdfDocument()
    assert document.load(str(destination)) == QPdfDocument.Error.None_
    assert document.pageCount() == result.page_count
    for index in range(document.pageCount()):
        image = document.render(index, QSize(595, 842))
        assert not image.isNull()
        body = image.copy(51, 51, 493, 712)
        assert any(
            body.pixelColor(x, y).value() < 250
            for y in range(0, body.height(), 4)
            for x in range(0, body.width(), 4)
        )
    document.close()


def test_missing_destination_directory_is_typed_and_redacted(
    tmp_path, valid_html, metadata
) -> None:
    destination = tmp_path / "PRIVATE-missing-sentinel" / "report.pdf"
    with pytest.raises(OutputWriteError) as caught:
        write_pdf_atomic(valid_html, destination, metadata)
    assert "PRIVATE-missing-sentinel" not in str(caught.value)
    assert caught.value.public_message == "The PDF file could not be written."


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission contract")
def test_unwritable_destination_directory_is_typed(
    tmp_path, valid_html, metadata
) -> None:
    directory = tmp_path / "unwritable"
    directory.mkdir()
    directory.chmod(0o500)
    try:
        with pytest.raises(OutputWriteError):
            write_pdf_atomic(valid_html, directory / "report.pdf", metadata)
        assert list(directory.glob(".*.tmp.pdf")) == []
    finally:
        directory.chmod(0o700)


def test_close_failure_cleans_created_temp_and_is_typed(
    tmp_path, valid_html, metadata, monkeypatch
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")
    real_close = os.close

    def fail_after_close(fd):
        real_close(fd)
        raise OSError("PRIVATE-close-sentinel")

    monkeypatch.setattr("json_to_pdf.pdf.os.close", fail_after_close)
    with pytest.raises(OutputWriteError) as caught:
        write_pdf_atomic(valid_html, destination, metadata)
    assert "PRIVATE-close-sentinel" not in str(caught.value)
    assert destination.read_bytes() == b"prior-pdf"
    assert list(tmp_path.glob(".*.tmp.pdf")) == []


def test_cleanup_failure_is_typed_and_preserves_destination(
    tmp_path, valid_html, metadata, monkeypatch
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")
    monkeypatch.setattr(
        "json_to_pdf.pdf._paint_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(RenderError()),
    )
    original_unlink = Path.unlink
    failed_once = False

    def fail_once(path, *args, **kwargs):
        nonlocal failed_once
        if path.name.endswith(".tmp.pdf") and not failed_once:
            failed_once = True
            raise OSError("PRIVATE-cleanup-sentinel")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_once)
    with pytest.raises(OutputWriteError) as caught:
        write_pdf_atomic(valid_html, destination, metadata)
    assert "PRIVATE-cleanup-sentinel" not in str(caught.value)
    assert destination.read_bytes() == b"prior-pdf"
    assert list(tmp_path.glob(".*.tmp.pdf")) == []


@pytest.mark.skipif(sys.platform != "win32", reason="Windows locking contract")
def test_locked_destination_failure_preserves_prior_bytes(
    tmp_path, valid_html, metadata
) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")
    with destination.open("rb"):
        with pytest.raises(OutputWriteError):
            write_pdf_atomic(valid_html, destination, metadata)
        assert destination.read_bytes() == b"prior-pdf"
    assert list(tmp_path.glob(".*.tmp.pdf")) == []
