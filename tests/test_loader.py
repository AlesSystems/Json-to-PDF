from pathlib import Path

import pytest

from json_to_pdf.errors import (
    InputReadError,
    InvalidJsonError,
    PolicyError,
    ResourceLimitError,
)
from json_to_pdf.loader import load_json
from json_to_pdf.limits import ResourceLimits
from json_to_pdf.model import JsonNumber


def test_preserves_valid_number_lexemes(tmp_path: Path) -> None:
    source = tmp_path / "numbers.json"
    source.write_text(
        '{"big":12345678901234567890,"decimal":1.2300e+40}', encoding="utf-8"
    )

    value = load_json(source).value

    assert value == {
        "big": JsonNumber("12345678901234567890"),
        "decimal": JsonNumber("1.2300e+40"),
    }


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_rejects_nonstandard_numbers(tmp_path: Path, token: str) -> None:
    source = tmp_path / "bad.json"
    source.write_text('{"value":' + token + "}", encoding="utf-8")

    with pytest.raises(InvalidJsonError, match="non-standard numeric constant"):
        load_json(source)


def test_rejects_duplicate_object_names_without_exposing_name(tmp_path: Path) -> None:
    source = tmp_path / "duplicates.json"
    source.write_text(
        '{"secret-value":"too-long-value","secret-value":"ok"}', encoding="utf-8"
    )

    with pytest.raises(PolicyError) as caught:
        load_json(source, ResourceLimits(max_string_chars=12))

    assert "secret-value" not in str(caught.value)


@pytest.mark.parametrize("payload", ["1", '"text"', "true", "null", "{}", "[]"])
def test_rejects_scalar_and_empty_roots(tmp_path: Path, payload: str) -> None:
    source = tmp_path / "root.json"
    source.write_text(payload, encoding="utf-8")

    with pytest.raises(PolicyError):
        load_json(source)


def test_accepts_file_at_byte_limit_and_rejects_one_byte_over(tmp_path: Path) -> None:
    source = tmp_path / "file.json"
    source.write_bytes(b"[0]")
    assert load_json(source, ResourceLimits(max_file_bytes=3)).value == [
        JsonNumber("0")
    ]

    with pytest.raises(ResourceLimitError):
        load_json(source, ResourceLimits(max_file_bytes=2))


def test_accepts_depth_at_limit_and_rejects_one_level_over(tmp_path: Path) -> None:
    source = tmp_path / "depth.json"
    source.write_text('{"a":"value"}', encoding="utf-8")
    assert load_json(source, ResourceLimits(max_depth=2)).value == {"a": "value"}

    source.write_text('{"a":{"b":"value"}}', encoding="utf-8")
    with pytest.raises(ResourceLimitError):
        load_json(source, ResourceLimits(max_depth=2))


def test_rejects_extreme_depth_without_exposing_parser_recursion(
    tmp_path: Path,
) -> None:
    source = tmp_path / "extreme-depth.json"
    source.write_text("[" * 10_000 + "0" + "]" * 10_000, encoding="utf-8")

    with pytest.raises(ResourceLimitError):
        load_json(source)


def test_does_not_misclassify_decoder_ceiling_as_configured_depth_limit(
    tmp_path: Path,
) -> None:
    source = tmp_path / "decoder-ceiling.json"
    source.write_text("[" * 10_000 + "0" + "]" * 10_000, encoding="utf-8")

    with pytest.raises(InvalidJsonError) as caught:
        load_json(source, ResourceLimits(max_depth=10_000))

    assert "recursion" not in str(caught.value).lower()


def test_accepts_node_count_at_limit_and_rejects_one_node_over(
    tmp_path: Path,
) -> None:
    source = tmp_path / "nodes.json"
    source.write_text("[0]", encoding="utf-8")
    assert load_json(source, ResourceLimits(max_nodes=2)).value == [JsonNumber("0")]

    source.write_text("[0,1]", encoding="utf-8")
    with pytest.raises(ResourceLimitError):
        load_json(source, ResourceLimits(max_nodes=2))


@pytest.mark.parametrize(
    ("payload", "limit"),
    [('{"abc":0}', 3), ('["abc"]', 3)],
)
def test_accepts_keys_and_strings_at_character_limit(
    tmp_path: Path, payload: str, limit: int
) -> None:
    source = tmp_path / "strings.json"
    source.write_text(payload, encoding="utf-8")

    load_json(source, ResourceLimits(max_string_chars=limit))


@pytest.mark.parametrize("payload", ['{"abcd":0}', '["abcd"]'])
def test_rejects_keys_and_strings_over_character_limit(
    tmp_path: Path, payload: str
) -> None:
    source = tmp_path / "strings.json"
    source.write_text(payload, encoding="utf-8")

    with pytest.raises(ResourceLimitError):
        load_json(source, ResourceLimits(max_string_chars=3))


def test_accepts_number_at_character_limit_and_rejects_one_over(
    tmp_path: Path,
) -> None:
    source = tmp_path / "number.json"
    source.write_text("[123]", encoding="utf-8")
    assert load_json(source, ResourceLimits(max_number_chars=3)).value == [
        JsonNumber("123")
    ]

    with pytest.raises(ResourceLimitError):
        load_json(source, ResourceLimits(max_number_chars=2))


def test_accepts_utf8_bom(tmp_path: Path) -> None:
    source = tmp_path / "bom.json"
    source.write_bytes(b'\xef\xbb\xbf{"value":true}')

    assert load_json(source).value == {"value": True}


def test_rejects_invalid_utf8_without_exposing_decoder_details(tmp_path: Path) -> None:
    source = tmp_path / "invalid-utf8.json"
    source.write_bytes(b'["\xff"]')

    with pytest.raises(InvalidJsonError) as caught:
        load_json(source)

    assert "xff" not in str(caught.value)


def test_reports_invalid_json_line_and_column(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text('{\n  "value":,\n}', encoding="utf-8")

    with pytest.raises(
        InvalidJsonError, match=r"invalid at line 2, column 11"
    ):
        load_json(source)


def test_redacts_missing_input_path(tmp_path: Path) -> None:
    source = tmp_path / "secret-value.json"

    with pytest.raises(InputReadError) as caught:
        load_json(source)

    assert "/secret/path" not in str(caught.value)
    assert "secret-value" not in str(caught.value)


def test_redacts_malformed_path(tmp_path: Path) -> None:
    source = tmp_path / "secret-value\0.json"

    with pytest.raises(InputReadError) as caught:
        load_json(source)

    assert "secret-value" not in str(caught.value)


def test_rejects_unreadable_input(tmp_path: Path) -> None:
    with pytest.raises(InputReadError):
        load_json(tmp_path)


def test_redacts_injected_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.json"
    source.write_text("[0]", encoding="utf-8")

    def fail_read(_path: Path) -> bytes:
        raise OSError("/secret/path secret-value")

    monkeypatch.setattr(Path, "read_bytes", fail_read)

    with pytest.raises(InputReadError) as caught:
        load_json(source)

    assert "/secret/path" not in str(caught.value)
    assert "secret-value" not in str(caught.value)
