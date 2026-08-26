from json_to_pdf.errors import InputReadError, InvalidJsonError
from json_to_pdf.limits import DEFAULT_LIMITS
from json_to_pdf.model import JsonNumber


def test_default_limits_are_exact() -> None:
    assert DEFAULT_LIMITS.max_file_bytes == 20 * 1024 * 1024
    assert DEFAULT_LIMITS.max_depth == 32
    assert DEFAULT_LIMITS.max_nodes == 200_000
    assert DEFAULT_LIMITS.max_string_chars == 100_000
    assert DEFAULT_LIMITS.max_number_chars == 1_000
    assert DEFAULT_LIMITS.max_title_chars == 200
    assert DEFAULT_LIMITS.max_pages == 2_000
    assert DEFAULT_LIMITS.max_pdf_bytes == 250 * 1024 * 1024


def test_json_number_retains_lexeme() -> None:
    assert JsonNumber("1.2300e+40") == "1.2300e+40"


def test_public_errors_do_not_leak_causes() -> None:
    error = InputReadError(cause=OSError("/secret/path and secret-value"))
    assert error.public_message == "The JSON file could not be read."
    assert "secret" not in error.public_message
    located = InvalidJsonError(line=3, column=8)
    assert located.public_message == "The JSON is invalid at line 3, column 8."
