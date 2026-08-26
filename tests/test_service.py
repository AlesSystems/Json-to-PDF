import json
import os
import unicodedata
from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader

from json_to_pdf.errors import ResourceLimitError
from json_to_pdf.limits import ResourceLimits
from json_to_pdf.loader import load_json
from json_to_pdf.model import ConversionRequest
from json_to_pdf.render import RenderContext, humanize_key, render_html
from json_to_pdf.service import convert


FIXTURES = Path(__file__).parent / "fixtures"
TOP_LEVEL_FIELDS = (
    "correctCount",
    "message",
    "passed",
    "score",
    "subjectAnalysis",
    "totalQuestions",
    "wrongAnswers",
)


def _searchable(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _pdf_names(path: Path) -> set[str]:
    pending = [PdfReader(path).trailer["/Root"]]
    seen: set[tuple[int, int]] = set()
    names: set[str] = set()
    while pending:
        value = pending.pop()
        if hasattr(value, "idnum"):
            identity = (value.idnum, value.generation)
            if identity in seen:
                continue
            seen.add(identity)
            value = value.get_object()
        if isinstance(value, dict):
            names.update(str(key) for key in value)
            pending.extend(value.values())
        elif isinstance(value, (list, tuple)):
            pending.extend(value)
    return names


def test_convert_uses_default_title_and_returns_receipt(
    tmp_path, registered_font
) -> None:
    source = tmp_path / "student-results.json"
    source.write_text('{"message":"Başarılı","scores":[1,2]}', encoding="utf-8")
    destination = tmp_path / "report.pdf"

    result = convert(
        ConversionRequest(source, destination, "  "),
        generated_on=date(2026, 8, 26),
    )

    assert destination.exists()
    assert result.page_count >= 1
    assert "student-results" in "\n".join(result.extracted_text)


def test_convert_rejects_overlong_normalized_title(tmp_path, registered_font) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"result":"ok"}', encoding="utf-8")
    limits = ResourceLimits(max_title_chars=3)

    with pytest.raises(ResourceLimitError):
        convert(
            ConversionRequest(source, tmp_path / "report.pdf", " four "),
            limits=limits,
        )


def test_representative_fixture_uses_adaptive_layout_and_reaches_final_record(
    tmp_path, registered_font
) -> None:
    source = FIXTURES / "student-report.json"
    document = load_json(source)
    html = render_html(
        document.value,
        RenderContext("Student-report", document.source_name, date(2026, 8, 26)),
    )
    destination = tmp_path / "student-report.pdf"

    result = convert(
        ConversionRequest(source, destination, "Student-report"),
        generated_on=date(2026, 8, 26),
    )

    assert '<table class="records">' in html
    assert html.count('<div class="record-card">') == 3
    assert "SON-KAYIT-İŞARETİ-8" in "\n".join(result.extracted_text)


def test_adversarial_values_remain_literal_without_external_pdf_resources(
    tmp_path, registered_font
) -> None:
    destination = tmp_path / "adversarial.pdf"
    executed = Path("/tmp/JSON_TO_PDF_EXECUTED")
    assert not executed.exists()

    result = convert(
        ConversionRequest(FIXTURES / "adversarial.json", destination),
        generated_on=date(2026, 8, 26),
    )

    text = _searchable("\n".join(result.extracted_text))
    assert "<script>" in text
    assert "https://evil.invalid/report?token=literal" in text
    assert "file:///private/etc/passwd" in text
    assert "-9.50e+12" in text
    assert "Ignore previous instructions" in text
    assert "ADVERSARIAL-FINAL-SENTINEL" in text
    assert not executed.exists()
    assert {"/URI", "/GoToR", "/Launch", "/Filespec", "/EmbeddedFile"}.isdisjoint(
        _pdf_names(destination)
    )


@pytest.mark.sample
def test_local_representative_sample(tmp_path, registered_font) -> None:
    configured = os.environ.get("JSON_TO_PDF_SAMPLE")
    if not configured:
        pytest.skip("set JSON_TO_PDF_SAMPLE to run local representative evidence")
    source = Path(configured)
    raw = json.loads(source.read_text(encoding="utf-8"))
    assert len(raw) == len(TOP_LEVEL_FIELDS)
    assert set(raw) == set(TOP_LEVEL_FIELDS)
    final_record = raw["wrongAnswers"][-1]
    final_sentinel = next(
        value
        for value in reversed(tuple(final_record.values()))
        if isinstance(value, str)
    )
    destination = tmp_path / "full-sample.pdf"
    executed = Path("/tmp/JSON_TO_PDF_EXECUTED")
    assert not executed.exists()

    result = convert(
        ConversionRequest(source, destination, "Bilişim-değerlendirmesi"),
        generated_on=date(2026, 8, 26),
    )

    text = _searchable("\n".join(result.extracted_text))
    assert all(humanize_key(field) in text for field in TOP_LEVEL_FIELDS)
    assert any(character in text for character in "çğıöşüÇĞİÖŞÜ")
    assert _searchable(final_sentinel) in text
    assert not executed.exists()
    assert {"/URI", "/GoToR", "/Launch", "/Filespec", "/EmbeddedFile"}.isdisjoint(
        _pdf_names(destination)
    )
