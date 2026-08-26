import json
import os
import socket
import unicodedata
from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader

from json_to_pdf.errors import PolicyError, ResourceLimitError, UnsupportedCharacterError
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
FORBIDDEN_PDF_NAMES = {
    "/URI",
    "/GoToR",
    "/Launch",
    "/Filespec",
    "/EmbeddedFile",
    "/EmbeddedFiles",
    "/EF",
    "/AF",
    "/AFRelationship",
    "/OpenAction",
    "/AA",
    "/JavaScript",
    "/JS",
}


def test_convert_rejects_same_source_and_destination_without_changing_source(
    tmp_path, registered_font
) -> None:
    source = tmp_path / "source.json"
    original = b'{"result":"unchanged"}'
    source.write_bytes(original)

    with pytest.raises(PolicyError) as caught:
        convert(ConversionRequest(source, tmp_path / "." / "source.json"))

    assert str(caught.value) == PolicyError.public_message
    assert str(source) not in str(caught.value)
    assert source.read_bytes() == original


def test_convert_rejects_existing_file_alias_without_changing_source(
    tmp_path, registered_font
) -> None:
    source = tmp_path / "source.json"
    alias = tmp_path / "alias.pdf"
    original = b'{"result":"unchanged"}'
    source.write_bytes(original)
    try:
        os.link(source, alias)
    except OSError:
        try:
            alias.symlink_to(source)
        except OSError:
            pytest.skip("filesystem does not support hardlinks or symlinks")

    with pytest.raises(PolicyError) as caught:
        convert(ConversionRequest(source, alias))

    assert str(caught.value) == PolicyError.public_message
    assert str(source) not in str(caught.value)
    assert source.read_bytes() == original


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


def test_convert_accepts_multiword_custom_title(tmp_path, registered_font) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"result":"ok"}', encoding="utf-8")

    result = convert(
        ConversionRequest(source, tmp_path / "report.pdf", "Student report"),
        generated_on=date(2026, 8, 26),
    )

    assert "Student report" in _searchable("\n".join(result.extracted_text))


def test_convert_accepts_spaced_source_and_default_title(tmp_path, registered_font) -> None:
    source = tmp_path / "student results.json"
    source.write_text('{"result":"ok"}', encoding="utf-8")

    result = convert(
        ConversionRequest(source, tmp_path / "report.pdf"),
        generated_on=date(2026, 8, 26),
    )

    text = _searchable("\n".join(result.extracted_text))
    assert "student results" in text
    assert "student results.json" in text


def test_convert_rejects_overlong_normalized_title(tmp_path, registered_font) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"result":"ok"}', encoding="utf-8")
    limits = ResourceLimits(max_title_chars=3)

    with pytest.raises(ResourceLimitError):
        convert(
            ConversionRequest(source, tmp_path / "report.pdf", " four "),
            limits=limits,
        )


def test_convert_font_gate_receives_all_text_but_not_numbers(
    tmp_path, registered_font, monkeypatch
) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        '{"outer":{"nestedKey":"nested value","number":12}}', encoding="utf-8"
    )
    observed: list[str] = []
    monkeypatch.setattr(
        "json_to_pdf.service.require_supported_text", observed.extend
    )

    convert(
        ConversionRequest(source, tmp_path / "report.pdf", "Custom title"),
        generated_on=date(2026, 8, 26),
    )

    assert observed == [
        "Custom title",
        "source.json",
        "outer",
        "nestedKey",
        "number",
        "nested value",
    ]


def test_convert_rejects_unsupported_nested_text(tmp_path, registered_font) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"nested":{"answer":"💩"}}', encoding="utf-8")

    with pytest.raises(UnsupportedCharacterError):
        convert(ConversionRequest(source, tmp_path / "report.pdf"))


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
    subject_table = html.split('<table class="records">', 1)[1].split("</table>", 1)[0]
    ordered_cells = (
        "<th>Subject</th>",
        "<th>Correct</th>",
        "<th>Wrong</th>",
        "<th>Score</th>",
        "<td>Donanım</td>",
        "<td>9</td>",
        "<td>1</td>",
        "<td>90</td>",
        "<td>Yazılım</td>",
    )
    positions = [subject_table.index(cell) for cell in ordered_cells]
    assert positions == sorted(positions)
    assert html.count('<div class="record-card">') == 3
    assert "SON-KAYIT-İŞARETİ-8" in "\n".join(result.extracted_text)


def test_adversarial_values_remain_literal_without_external_pdf_resources(
    tmp_path, registered_font, monkeypatch
) -> None:
    destination = tmp_path / "adversarial.pdf"
    executed = Path("/tmp/JSON_TO_PDF_EXECUTED")
    assert not executed.exists()
    network_requests = []

    def fail_network(*args, **kwargs):
        network_requests.append((args, kwargs))
        raise AssertionError("conversion attempted a network request")

    monkeypatch.setattr(socket.socket, "connect", fail_network)
    monkeypatch.setattr(socket, "create_connection", fail_network)

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
    assert network_requests == []
    assert not executed.exists()
    assert FORBIDDEN_PDF_NAMES.isdisjoint(_pdf_names(destination))


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
    assert FORBIDDEN_PDF_NAMES.isdisjoint(_pdf_names(destination))
