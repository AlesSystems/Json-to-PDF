# JSON-to-PDF Desktop Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small offline desktop application that safely converts generic JSON into a readable, searchable, validated PDF for students.

**Architecture:** A bounded standard-library JSON loader produces a typed recursive tree whose numbers retain their source lexemes. A pure renderer escapes that tree into Qt-supported rich-text HTML; a worker-thread `QTextDocument`/`QPrinter` pipeline paginates it, writes beside the destination, validates it strictly with pypdf, and atomically replaces the output. Qt Widgets provides the only GUI.

**Tech Stack:** CPython 3.12, PySide6 6.11.2, pypdf 6.16.1, pytest 9.1.1, pytest-qt 4.5.0, Noto Sans v2.015, `pyside6-deploy`/Nuitka 4.1.1.

**Spec:** `docs/architecture.md`

## Global Constraints

- Support Windows 10/11 x86-64, macOS 13+ universal2, and Linux x86-64 with glibc 2.34+.
- Enforce 20 MiB input, depth 32, 200,000 JSON values, 100,000 characters per key/string, 1,000 characters per number, 200 title characters, 2,000 output pages, and 250 MiB generated PDF.
- Accept UTF-8 with optional BOM; accept only non-empty object/array roots; reject `NaN`, `Infinity`, and `-Infinity`.
- Treat every JSON value as untrusted data. Never interpret HTML, URLs, file paths, image strings, or instructions embedded in values.
- Perform no network I/O at runtime and never echo source values, full paths, or internal exception text in public errors.
- Use only the exact bundled Noto Sans asset; reject unsupported printable code points instead of silently falling back.
- Generate A4 portrait with 18 mm margins, a 7 mm footer, a 3 mm body/footer gap, at least 10 pt body type, 135% line height, and `Page N of M`.
- Validate the temporary PDF before replacement. A failure must preserve any prior destination and clean the temporary file.
- Do not claim PDF/UA, all-Unicode, crash durability, image support, batch conversion, templates, plugins, preview, telemetry, or cloud features.
- Follow TDD and commit each task with the exact Conventional Commit message shown.

---

## File Map

| Path | Responsibility |
|---|---|
| `pyproject.toml`, `requirements.lock` | package metadata, exact runtime/dev versions, pytest configuration |
| `src/json_to_pdf/model.py` | recursive JSON types and immutable request/result records |
| `src/json_to_pdf/errors.py` | stable redacted public error taxonomy |
| `src/json_to_pdf/limits.py` | immutable resource policy |
| `src/json_to_pdf/font.py` | exact asset verification, registration, glyph coverage |
| `src/json_to_pdf/loader.py` | bounded UTF-8 JSON loading and validation |
| `src/json_to_pdf/render.py` | pure adaptive escaped HTML rendering |
| `src/json_to_pdf/pdf.py` | pagination, temporary output, strict validation, replacement |
| `src/json_to_pdf/service.py` | synchronous conversion orchestration |
| `src/json_to_pdf/gui.py` | accessible Qt Widgets workflow and worker-thread lifecycle |
| `src/json_to_pdf/__main__.py` | GUI entry and internal packaged smoke-conversion entry |
| `tests/fixtures/` | deterministic generic, adversarial, and representative JSON data |
| `pysidedeploy.spec`, `.github/workflows/release.yml` | native standalone packaging and OS matrix proof |
| `docs/quality-checklist.md`, `THIRD_PARTY_NOTICES.md` | human acceptance and distribution notices |

### Task 1: Lock the project and test environment

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.lock`
- Create: `src/json_to_pdf/__init__.py`
- Create: `tests/test_project.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: none
- Produces: importable `json_to_pdf` package; exact dependency set; tracked `pysidedeploy.spec`

- [ ] **Step 1: Write the failing project-contract test**

```python
# tests/test_project.py
from importlib.metadata import version


def test_pinned_runtime_versions() -> None:
    assert version("PySide6") == "6.11.2"
    assert version("pypdf") == "6.16.1"
```

- [ ] **Step 2: Run the test and verify the missing package/config failure**

Run: `python -m pytest tests/test_project.py -q`

Expected: FAIL during import or version lookup before the locked environment is installed.

- [ ] **Step 3: Add exact package metadata and lock content**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "json-to-pdf"
version = "0.1.0"
requires-python = "==3.12.*"
dependencies = ["PySide6==6.11.2", "pypdf==6.16.1"]

[project.optional-dependencies]
dev = ["pytest==9.1.1", "pytest-qt==4.5.0", "Nuitka==4.1.1"]

[tool.pytest.ini_options]
qt_api = "pyside6"
testpaths = ["tests"]
```

```text
# requirements.lock
PySide6==6.11.2
pypdf==6.16.1
pytest==9.1.1
pytest-qt==4.5.0
Nuitka==4.1.1
```

Append `!pysidedeploy.spec` after the existing `*.spec` rule in `.gitignore`.

- [ ] **Step 4: Install the lock and run the project-contract test**

Run: `python -m pip install -r requirements.lock && python -m pytest tests/test_project.py -q`

Expected: PASS, `1 passed`.

- [ ] **Step 5: Commit the environment contract**

```bash
git add .gitignore pyproject.toml requirements.lock src/json_to_pdf/__init__.py tests/test_project.py
git commit -m "build: pin supported Python and dependencies"
```

### Task 2: Define immutable data, limits, and redacted errors

**Files:**
- Create: `src/json_to_pdf/model.py`
- Create: `src/json_to_pdf/limits.py`
- Create: `src/json_to_pdf/errors.py`
- Create: `tests/test_contracts.py`

**Interfaces:**
- Consumes: package from Task 1
- Produces: `JsonNumber`, `JsonValue`, `LoadedDocument`, `ResourceLimits`, `DEFAULT_LIMITS`, and typed `ConversionError` subclasses

- [ ] **Step 1: Write failing tests for the limits, number type, and redaction**

```python
# tests/test_contracts.py
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
```

- [ ] **Step 2: Run the focused test and see missing-module failures**

Run: `python -m pytest tests/test_contracts.py -q`

Expected: FAIL because `model`, `limits`, and `errors` do not exist.

- [ ] **Step 3: Implement the exact contracts**

```python
# src/json_to_pdf/model.py
from dataclasses import dataclass
from pathlib import Path


class JsonNumber(str):
    pass


JsonScalar = bool | str | JsonNumber | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class LoadedDocument:
    value: dict[str, JsonValue] | list[JsonValue]
    source_name: str


@dataclass(frozen=True)
class ConversionRequest:
    source: Path
    destination: Path
    title: str | None = None
```

Implement `ResourceLimits` exactly as specified in `docs/architecture.md`. Implement `ConversionError(cause: Exception | None = None)` plus `InputReadError`, `InvalidJsonError`, `PolicyError`, `ResourceLimitError`, `UnsupportedCharacterError`, `RenderError`, `PdfValidationError`, and `OutputWriteError`. Only `InvalidJsonError` with a standard decoder location and `UnsupportedCharacterError` with `U+XXXX` may interpolate safe structured data.

- [ ] **Step 4: Run the focused contract tests**

Run: `python -m pytest tests/test_contracts.py -q`

Expected: PASS, `3 passed`.

- [ ] **Step 5: Commit the shared contracts**

```bash
git add src/json_to_pdf/model.py src/json_to_pdf/limits.py src/json_to_pdf/errors.py tests/test_contracts.py
git commit -m "feat(core): define bounded conversion contracts"
```

### Task 3: Pin, register, and verify the bundled font

**Files:**
- Create: `src/json_to_pdf/assets/fonts/NotoSans[wdth,wght].ttf`
- Create: `src/json_to_pdf/assets/fonts/OFL.txt`
- Create: `src/json_to_pdf/font.py`
- Create: `tests/conftest.py`
- Create: `tests/test_font.py`

**Interfaces:**
- Consumes: `UnsupportedCharacterError` from Task 2
- Produces: `FONT_FAMILY`, `register_bundled_font() -> str`, `require_supported_text(texts: Iterable[str]) -> None`

- [ ] **Step 1: Write failing hash, registration, and coverage tests**

```python
# tests/test_font.py
from hashlib import sha256
from pathlib import Path

import pytest

from json_to_pdf.errors import UnsupportedCharacterError
from json_to_pdf.font import register_bundled_font, require_supported_text

FONT = Path("src/json_to_pdf/assets/fonts/NotoSans[wdth,wght].ttf")
OFL = Path("src/json_to_pdf/assets/fonts/OFL.txt")


def test_font_assets_are_exact() -> None:
    assert sha256(FONT.read_bytes()).hexdigest() == "bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d"
    assert sha256(OFL.read_bytes()).hexdigest() == "cee9892f9f0cc8fe882c9e9537ee6a89621d86ee7ceaf70b02e2b2b1c25c061a"


def test_turkish_glyphs_are_supported(qapp) -> None:
    assert register_bundled_font() == "Noto Sans"
    require_supported_text(["ÇĞİÖŞÜçğıöşü"])


def test_unsupported_character_is_rejected(qapp) -> None:
    register_bundled_font()
    with pytest.raises(UnsupportedCharacterError, match="U\\+"):
        require_supported_text(["\U0001F9EA"])
```

- [ ] **Step 2: Run the font tests and see missing-asset/module failures**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_font.py -q`

Expected: FAIL because the font assets and loader are absent.

- [ ] **Step 3: Add the exact assets and font gate**

Download both files from Google Fonts commit `6a003b5eb672dc8bf5bff5937cf5863f8b175445`, verify the two hashes above before adding them, and implement:

```python
# src/json_to_pdf/font.py
from collections.abc import Iterable
from importlib.resources import files

from PySide6.QtGui import QFontDatabase, QRawFont

from .errors import UnsupportedCharacterError

FONT_FAMILY = "Noto Sans"
_raw_font: QRawFont | None = None


def register_bundled_font() -> str:
    global _raw_font
    path = files("json_to_pdf").joinpath("assets/fonts/NotoSans[wdth,wght].ttf")
    font_id = QFontDatabase.addApplicationFont(str(path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if FONT_FAMILY not in families:
        raise RuntimeError("The bundled report font could not be loaded.")
    _raw_font = QRawFont(str(path), 10.0)
    if not _raw_font.isValid():
        raise RuntimeError("The bundled report font could not be loaded.")
    return FONT_FAMILY


def require_supported_text(texts: Iterable[str]) -> None:
    if _raw_font is None:
        raise RuntimeError("The bundled report font is not registered.")
    for char in set().union(*(set(text) for text in texts)):
        if char in "\n\r\t":
            continue
        if ord(char) < 32 or not _raw_font.supportsCharacter(ord(char)):
            raise UnsupportedCharacterError(ord(char))
```

Add a session-scoped `registered_font(qapp)` fixture in `tests/conftest.py` that calls `register_bundled_font()` and returns `FONT_FAMILY`.

- [ ] **Step 4: Run the font test suite**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_font.py -q`

Expected: PASS, `3 passed`.

- [ ] **Step 5: Commit the verified typography boundary**

```bash
git add src/json_to_pdf/assets/fonts src/json_to_pdf/font.py tests/conftest.py tests/test_font.py
git commit -m "feat(font): bundle and verify Noto Sans typography"
```

### Task 4: Load JSON with lexical numbers and hard resource bounds

**Files:**
- Create: `src/json_to_pdf/loader.py`
- Create: `tests/test_loader.py`

**Interfaces:**
- Consumes: `JsonNumber`, `LoadedDocument`, errors, and limits from Task 2
- Produces: `load_json(path: Path, limits: ResourceLimits = DEFAULT_LIMITS) -> LoadedDocument`

- [ ] **Step 1: Write failing parser-policy tests**

```python
# tests/test_loader.py
from pathlib import Path

import pytest

from json_to_pdf.errors import InvalidJsonError, PolicyError, ResourceLimitError
from json_to_pdf.loader import load_json
from json_to_pdf.model import JsonNumber


def test_preserves_valid_number_lexemes(tmp_path: Path) -> None:
    source = tmp_path / "numbers.json"
    source.write_text('{"big":12345678901234567890,"decimal":1.2300e+40}', encoding="utf-8")
    value = load_json(source).value
    assert value == {"big": JsonNumber("12345678901234567890"), "decimal": JsonNumber("1.2300e+40")}


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_rejects_nonstandard_numbers(tmp_path: Path, token: str) -> None:
    source = tmp_path / "bad.json"
    source.write_text('{"value":' + token + "}", encoding="utf-8")
    with pytest.raises(InvalidJsonError, match="non-standard numeric constant"):
        load_json(source)


@pytest.mark.parametrize("payload", ["1", '"text"', "true", "null", "{}", "[]"])
def test_rejects_scalar_and_empty_roots(tmp_path: Path, payload: str) -> None:
    source = tmp_path / "root.json"
    source.write_text(payload, encoding="utf-8")
    with pytest.raises(PolicyError):
        load_json(source)
```

- [ ] **Step 2: Run the parser tests and verify they fail**

Run: `python -m pytest tests/test_loader.py -q`

Expected: FAIL because `load_json` does not exist.

- [ ] **Step 3: Implement bounded decoding and parser callbacks**

```python
# core of src/json_to_pdf/loader.py
def load_json(path: Path, limits: ResourceLimits = DEFAULT_LIMITS) -> LoadedDocument:
    try:
        if path.stat().st_size > limits.max_file_bytes:
            raise ResourceLimitError("file size")
        raw = path.read_bytes()
    except ResourceLimitError:
        raise
    except OSError as error:
        raise InputReadError(cause=error) from error
    if len(raw) > limits.max_file_bytes:
        raise ResourceLimitError("file size")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidJsonError() from error

    def number(token: str) -> JsonNumber:
        if len(token) > limits.max_number_chars:
            raise ResourceLimitError("number length")
        return JsonNumber(token)

    def constant(token: str) -> None:
        raise InvalidJsonError(nonstandard_constant=token)

    try:
        value = json.loads(text, parse_int=number, parse_float=number, parse_constant=constant)
    except json.JSONDecodeError as error:
        raise InvalidJsonError(line=error.lineno, column=error.colno) from error
    if not isinstance(value, (dict, list)) or not value:
        raise PolicyError("The JSON root must be a non-empty object or array.")
    _validate_tree(value, limits)
    return LoadedDocument(value=value, source_name=path.name)
```

Implement `_validate_tree` with a stack of `(value, depth)` tuples. Increment the count once per popped JSON value, reject depth above 32, reject count above 200,000, and inspect object keys plus string/`JsonNumber` lengths without recursively calling Python.

- [ ] **Step 4: Add boundary and redaction tests**

Add at/over tests for file bytes, depth, node count, key/string length, number length, UTF-8 BOM, invalid UTF-8, invalid JSON line/column, missing/unreadable input, and injected `OSError("/secret/path secret-value")`. Assert the safe public message contains neither sentinel.

- [ ] **Step 5: Run the complete loader test**

Run: `python -m pytest tests/test_loader.py -q`

Expected: PASS for all parser, policy, boundary, and redaction cases.

- [ ] **Step 6: Commit the bounded loader**

```bash
git add src/json_to_pdf/loader.py tests/test_loader.py
git commit -m "feat(loader): preserve and bound generic JSON data"
```

### Task 5: Render the typed tree into safe adaptive rich text

**Files:**
- Create: `src/json_to_pdf/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `JsonValue`/`JsonNumber` from Task 2 and font family from Task 3
- Produces: `RenderContext`, `humanize_key(key: str) -> str`, `render_html(value, context) -> str`

- [ ] **Step 1: Write failing renderer classification tests**

```python
# tests/test_render.py
from datetime import date

from json_to_pdf.model import JsonNumber
from json_to_pdf.render import RenderContext, humanize_key, render_html

CTX = RenderContext("Exam Results", "results.json", date(2026, 8, 26))


def test_humanizes_labels_without_changing_values() -> None:
    assert humanize_key("correctAnswer") == "Correct Answer"
    html = render_html({"correctAnswer": "HTTPStatus2"}, CTX)
    assert "Correct Answer" in html
    assert "HTTPStatus2" in html


def test_selects_table_only_for_narrow_short_rows() -> None:
    table = render_html([{"subject": "A", "total": JsonNumber("2")}], CTX)
    cards = render_html([{"a": "x", "b": "y", "c": "z", "d": "q", "e": "too wide"}], CTX)
    assert '<table class="records">' in table
    assert 'class="record-card"' in cards


def test_escapes_all_untrusted_text() -> None:
    html = render_html({"<img src=x>": "<script>https://example.test</script>"}, CTX)
    assert "<script>" not in html and "<img src=x>" not in html
    assert "&lt;script&gt;https://example.test&lt;/script&gt;" in html
```

- [ ] **Step 2: Run renderer tests and verify missing-interface failures**

Run: `python -m pytest tests/test_render.py -q`

Expected: FAIL because `render.py` is absent.

- [ ] **Step 3: Implement pure scalar formatting and adaptive dispatch**

```python
# selected contracts in src/json_to_pdf/render.py
def _scalar_text(value: JsonScalar) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _is_table(records: list[dict[str, JsonValue]]) -> bool:
    if not records or any(list(row) != list(records[0]) for row in records[1:]):
        return False
    keys = list(records[0])
    if len(keys) > 4 or any(not _is_scalar(value) for row in records for value in row.values()):
        return False
    widths = [max(len(_scalar_text(row[key])) for row in records) for key in keys]
    return max(widths, default=0) <= 60 and sum(widths) <= 120
```

Build fragments into a list and `"".join(...)` once. Escape title, filename, key labels, and scalar strings with `html.escape(..., quote=True)`. Emit exactly one H1, logical H2/H3 sections, two-column definition tables, `<thead>` for record tables, ordered primitive lists, record cards for wide/long object arrays, and numbered sections for mixed arrays. Use only properties documented by Qt's rich-text subset.

- [ ] **Step 4: Add the complete recursive/adversarial matrix**

Test object rows, a four-column table, five-column/card fallback, 60/61-character boundary, 120/121 summed-width boundary, primitive arrays, nested objects, mixed arrays, null/boolean/number lexical spelling, stable source order, long Turkish text, quotes/ampersands, `file:///`, URLs, `<img>`, and `<a>`. Assert the HTML contains no active anchor/image/script or external stylesheet.

- [ ] **Step 5: Run the renderer suite**

Run: `python -m pytest tests/test_render.py -q`

Expected: PASS for classification, escaping, order, and scalar semantics.

- [ ] **Step 6: Commit the pure renderer**

```bash
git add src/json_to_pdf/render.py tests/test_render.py
git commit -m "feat(render): format JSON as safe adaptive rich text"
```

### Task 6: Prove Qt pagination and footer geometry

**Files:**
- Create: `src/json_to_pdf/pdf.py`
- Create: `tests/test_pagination.py`

**Interfaces:**
- Consumes: registered font from Task 3, rendered HTML from Task 5, limits/errors from Task 2
- Produces: `PdfMetadata` and private `_paint_document(html_text: str, output: Path, metadata: PdfMetadata, limits: ResourceLimits) -> int`

- [ ] **Step 1: Write the failing multi-page proof**

```python
# tests/test_pagination.py
from datetime import date

from pypdf import PdfReader

from json_to_pdf.pdf import PdfMetadata, _paint_document


def test_footer_pagination_has_no_extra_page(tmp_path, registered_font) -> None:
    html = "<h1>FIRST-SENTINEL</h1>" + "<p>Long Turkish text ÇĞİÖŞÜ.</p>" * 700 + "<p>LAST-SENTINEL</p>"
    output = tmp_path / "pages.pdf"
    count = _paint_document(html, output, PdfMetadata("Title", "fixture.json", date(2026, 8, 26)))
    reader = PdfReader(output, strict=True)
    text = [page.extract_text() or "" for page in reader.pages]
    assert len(reader.pages) == count >= 2
    assert "FIRST-SENTINEL" in text[0]
    assert "LAST-SENTINEL" in text[-1]
    assert [f"Page {i} of {count}" in page for i, page in enumerate(text, 1)] == [True] * count
```

- [ ] **Step 2: Run the proof and verify it fails on the missing painter**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_pagination.py -q`

Expected: FAIL because `_paint_document` is absent.

- [ ] **Step 3: Implement exact body/footer pagination**

Define the `PdfMetadata` frozen dataclass exactly as specified in `docs/architecture.md`, then implement the following geometry:

```python
# core geometry/loop for src/json_to_pdf/pdf.py
printer = QPrinter(QPrinter.PrinterMode.HighResolution)
printer.setResolution(72)
printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
printer.setOutputFileName(str(output))
layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                     QMarginsF(18, 18, 18, 18), QPageLayout.Unit.Millimeter)
if not printer.setPageLayout(layout):
    raise RenderError()
paint = printer.pageLayout().paintRectPixels(printer.resolution())
mm = printer.resolution() / 25.4
footer_height, footer_gap = 7 * mm, 3 * mm
body = QRectF(paint.left(), paint.top(), paint.width(), paint.height() - footer_height - footer_gap)
footer = QRectF(paint.left(), body.bottom() + footer_gap, paint.width(), footer_height)

document = QTextDocument()
document.setDefaultFont(QFont(FONT_FAMILY, 10))
option = document.defaultTextOption()
option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
document.setDefaultTextOption(option)
document.setDocumentMargin(0)
document.setHtml(html_text)
document.documentLayout().setPaintDevice(printer)
document.setPageSize(body.size())
document.documentLayout().documentSize()  # force layout
pages = document.pageCount()
```

Begin the painter and, for every page, save; translate to `body.left(), body.top()`; set `PaintContext.clip` to `QRectF(0, i * body.height(), body.width(), body.height())`; translate vertically by `-i * body.height()`; draw; restore; draw the footer; and call `printer.newPage()` only when another page remains. Check `begin()`, every `newPage()`, and `end()` and reject page counts outside `1..limits.max_pages`.

- [ ] **Step 4: Add geometry failure and adversarial wrapping checks**

Add tests for a one-page document, an exact last-page boundary, 80 unbroken characters, four-column table, record card, long Turkish prose, mocked `QPainter.begin/end` and `QPrinter.newPage` failures, A4 media boxes, and max-page rejection. Use pypdf extraction to assert no blank page and first/last sentinels.

- [ ] **Step 5: Run the pagination proof suite**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_pagination.py -q`

Expected: PASS with no blank trailing page and correct footer sequence.

- [ ] **Step 6: Commit the highest-risk proof**

```bash
git add src/json_to_pdf/pdf.py tests/test_pagination.py
git commit -m "test(pdf): prove bounded footer pagination"
```

### Task 7: Add strict PDF validation and safe replacement

**Files:**
- Modify: `src/json_to_pdf/pdf.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_pdf.py`

**Interfaces:**
- Consumes: `_paint_document` from Task 6
- Produces: `PdfValidationResult`, `validate_pdf(...)`, `write_pdf_atomic(...)` with signatures from `docs/architecture.md`

- [ ] **Step 1: Write failing strict-validation and preservation tests**

```python
# tests/test_pdf.py
def test_atomic_failure_preserves_destination(tmp_path, valid_html, metadata, monkeypatch) -> None:
    destination = tmp_path / "report.pdf"
    destination.write_bytes(b"prior-pdf")

    def fail_validation(*args, **kwargs):
        raise PdfValidationError()

    monkeypatch.setattr("json_to_pdf.pdf.validate_pdf", fail_validation)
    with pytest.raises(PdfValidationError):
        write_pdf_atomic(valid_html, destination, metadata)
    assert destination.read_bytes() == b"prior-pdf"
    assert list(tmp_path.glob(".*.tmp.pdf")) == []


def test_strict_validation_rejects_corrupt_pdf(tmp_path) -> None:
    corrupt = tmp_path / "bad.pdf"
    corrupt.write_bytes(b"%PDF-1.7\ncorrupt")
    with pytest.raises(PdfValidationError):
        validate_pdf(corrupt, expected_title="Title", expected_source_name="source.json")
```

Add concrete `valid_html` and `metadata` fixtures to `tests/conftest.py`; use the fixed title `Title`, source `source.json`, date `2026-08-26`, and Turkish body sentinel `Başarılı`.

- [ ] **Step 2: Run PDF boundary tests and verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_pdf.py -q`

Expected: FAIL because validation and atomic replacement are absent.

- [ ] **Step 3: Implement strict bounded validation**

Open the PDF in a `with path.open("rb")` block; reject `path.stat().st_size > max_pdf_bytes`; construct `PdfReader(stream, strict=True)`; reject encryption and page counts outside `1..max_pages`; extract every page while the stream is open; reject empty content pages; require title and source filename in combined text; then close the stream before returning `PdfValidationResult(page_count, tuple(texts))`. Translate every pypdf/OS exception into a redacted typed error.

- [ ] **Step 4: Implement same-directory temporary output and replacement**

```python
fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp.pdf", dir=destination.parent)
os.close(fd)  # required before Qt/pypdf, especially on Windows
temp = Path(temp_name)
try:
    _paint_document(html_text, temp, metadata, limits)
    result = validate_pdf(temp, expected_title=metadata.title,
                          expected_source_name=metadata.source_name, limits=limits)
    os.replace(temp, destination)
    return result
except ConversionError:
    raise
except OSError as error:
    raise OutputWriteError(cause=error) from error
finally:
    temp.unlink(missing_ok=True)
```

- [ ] **Step 5: Add the real-filesystem and injected-failure matrix**

Test successful replacement, strict reader failure, blank PDF, encrypted PDF, oversized PDF, too many pages, painter failure, replacement failure, cleanup failure, missing/unwritable directory, and redaction sentinels. Run successful replacement/prior-byte preservation/temp cleanup with real files on every OS. Add a Windows-only test that keeps the destination handle open, expects typed failure, verifies old bytes, then closes it; do not assert the same lock behavior on Unix.

- [ ] **Step 6: Prove embedded font and rasterized nonblank pages**

Use pypdf page resources to require a `/FontDescriptor` containing `/FontFile`, `/FontFile2`, or `/FontFile3`. Load the generated PDF with `PySide6.QtPdf.QPdfDocument`, render every page to `QImage`, and assert each body image contains non-white pixels. Assert no page annotations arise from URL/HTML-looking values.

- [ ] **Step 7: Run the complete PDF suite**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_pagination.py tests/test_pdf.py -q`

Expected: PASS for pagination, validation, embedding, rasterization, and replacement.

- [ ] **Step 8: Commit the production PDF boundary**

```bash
git add src/json_to_pdf/pdf.py tests/conftest.py tests/test_pdf.py
git commit -m "feat(pdf): validate and safely replace searchable PDFs"
```

### Task 8: Orchestrate conversion and verify representative data

**Files:**
- Create: `src/json_to_pdf/service.py`
- Create: `tests/test_service.py`
- Create: `tests/fixtures/student-report.json`
- Create: `tests/fixtures/adversarial.json`

**Interfaces:**
- Consumes: loader, font gate, renderer, and PDF writer from Tasks 3–7
- Produces: `convert(request, *, limits=DEFAULT_LIMITS, generated_on=None) -> PdfValidationResult`

- [ ] **Step 1: Write the failing service-order and title tests**

```python
# tests/test_service.py
from datetime import date

from json_to_pdf.model import ConversionRequest
from json_to_pdf.service import convert


def test_convert_uses_default_title_and_returns_receipt(tmp_path, registered_font) -> None:
    source = tmp_path / "student-results.json"
    source.write_text('{"message":"Başarılı","scores":[1,2]}', encoding="utf-8")
    destination = tmp_path / "report.pdf"
    result = convert(ConversionRequest(source, destination, "  "), generated_on=date(2026, 8, 26))
    assert destination.exists()
    assert result.page_count >= 1
    assert "student-results" in "\n".join(result.extracted_text)
```

- [ ] **Step 2: Run the service test and see the missing service failure**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_service.py -q`

Expected: FAIL because `service.py` is absent.

- [ ] **Step 3: Implement the single orchestration path**

```python
def convert(request: ConversionRequest, *, limits: ResourceLimits = DEFAULT_LIMITS,
            generated_on: date | None = None) -> PdfValidationResult:
    document = load_json(request.source, limits)
    title = request.title.strip() if request.title and request.title.strip() else request.source.stem
    if len(title) > limits.max_title_chars:
        raise ResourceLimitError("title length")
    texts = [title, document.source_name, *_iter_keys_and_strings(document.value)]
    require_supported_text(texts)
    context = RenderContext(title, document.source_name, generated_on or date.today())
    html_text = render_html(document.value, context)
    metadata = PdfMetadata(title, document.source_name, context.generated_on)
    return write_pdf_atomic(html_text, request.destination, metadata, limits)


def _iter_keys_and_strings(root: JsonValue) -> Iterable[str]:
    stack = [root]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            yield from value.keys()
            stack.extend(reversed(list(value.values())))
        elif isinstance(value, list):
            stack.extend(reversed(value))
        elif isinstance(value, str) and not isinstance(value, JsonNumber):
            yield value
```

- [ ] **Step 4: Add representative and adversarial integration fixtures**

Create `student-report.json` with the sample's seven top-level field names, two short `subjectAnalysis` rows, and at least three long `wrongAnswers` records using synthetic Turkish text. Assert summary renders as a four-column table, wrong answers as cards, and the final-record sentinel survives PDF extraction. Create `adversarial.json` with HTML, URLs, `file:///`, long tokens, nulls, exponent numbers, and strings that resemble instructions; assert all are literal data and no network/resource access occurs.

- [ ] **Step 5: Add the local full-sample evidence lane**

Mark a test `@pytest.mark.sample` that reads `JSON_TO_PDF_SAMPLE` only when explicitly set. Run it with `/Users/altanesmer/Desktop/bilisim_questions.json`, assert all seven top-level fields appear, the PDF contains Turkish text and a final-record sentinel, and no value is executed or treated as an instruction. Keep the synthetic fixture in normal CI; never commit the user's sample without permission.

- [ ] **Step 6: Run service and sample tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_service.py -q`

Run locally: `JSON_TO_PDF_SAMPLE=/Users/altanesmer/Desktop/bilisim_questions.json QT_QPA_PLATFORM=offscreen python -m pytest tests/test_service.py -m sample -q`

Expected: both commands PASS; CI remains independent of the desktop file.

- [ ] **Step 7: Commit the end-to-end service**

```bash
git add src/json_to_pdf/service.py tests/test_service.py tests/fixtures/student-report.json tests/fixtures/adversarial.json
git commit -m "feat(service): convert generic JSON through one safe pipeline"
```

### Task 9: Build the accessible responsive GUI and smoke entry

**Files:**
- Create: `src/json_to_pdf/gui.py`
- Create: `src/json_to_pdf/__main__.py`
- Create: `tests/test_gui.py`
- Create: `tests/test_main.py`

**Interfaces:**
- Consumes: `ConversionRequest`, `convert`, and font registration
- Produces: `MainWindow`, worker-object success/failure signals, `main(argv: Sequence[str] | None = None) -> int`

- [ ] **Step 1: Write failing accessibility/workflow tests**

```python
# tests/test_gui.py
def test_form_is_labeled_and_keyboard_ordered(qtbot, registered_font) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.source_label.buddy() is window.source_edit
    assert window.destination_label.buddy() is window.destination_edit
    assert window.title_label.buddy() is window.title_edit
    assert window.generate_button.accessibleName() == "Generate PDF"
    assert not window.open_button.isEnabled()


def test_conversion_does_not_block_event_loop(qtbot, window, blocking_converter) -> None:
    window.start_conversion(blocking_converter.request)
    assert not window.generate_button.isEnabled()
    qtbot.waitUntil(lambda: window.status_label.text() == "Generating PDF…")
    blocking_converter.finish_success()
    qtbot.waitUntil(window.open_button.isEnabled)
```

- [ ] **Step 2: Run GUI tests and verify missing-window failures**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui.py tests/test_main.py -q`

Expected: FAIL because GUI and entry point are absent.

- [ ] **Step 3: Implement the minimal Qt Widgets form**

Use `QLineEdit` fields for source/destination/title, associated `QLabel.setBuddy`, JSON/PDF browse dialogs, Generate/Open buttons, and a status label. Set accessible names, explicit tab order, JSON/PDF filters, and required-field validation. Do not add preview, theme, settings, menus, or drag-and-drop.

- [ ] **Step 4: Implement worker-object thread ownership**

Create a `QObject` worker with immutable `ConversionRequest`, `finished(PdfValidationResult)` and `failed(ConversionError)` signals. Move it to a fresh `QThread`; create/use/destroy `QTextDocument`, `QPrinter`, and `QPainter` only through `convert` in that thread; connect results with queued signals; stop/delete the thread and worker after either outcome. Never read or write a widget from the worker.

- [ ] **Step 5: Add GUI success/error/redaction/open tests**

Test disabled Generate while active, restored state on success/failure, visible status, typed actionable dialog, no leaked `/secret/path` or `secret-value`, Open Result calling `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`, and a false open result producing a separate warning without changing conversion success.

- [ ] **Step 6: Add the internal packaged smoke path**

In `main(argv)`, register the font before either path. With `--smoke-convert SOURCE DESTINATION`, call `convert`, return 0 on success and 1 on typed failure without opening a window. With no flag, construct and show `MainWindow`. Test both argument paths with spies; do not implement a second converter.

- [ ] **Step 7: Run GUI and entry tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui.py tests/test_main.py -q`

Expected: PASS for labels, focus, responsiveness, thread cleanup, errors, Open Result, and smoke arguments.

- [ ] **Step 8: Commit the desktop workflow**

```bash
git add src/json_to_pdf/gui.py src/json_to_pdf/__main__.py tests/test_gui.py tests/test_main.py
git commit -m "feat(gui): add an accessible responsive conversion window"
```

### Task 10: Package standalone artifacts on all target systems

**Files:**
- Create: `pysidedeploy.spec`
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `python -m json_to_pdf` entry and exact assets
- Produces: native standalone artifacts and packaged `--smoke-convert` proof

- [ ] **Step 1: Initialize and inspect the deployment spec**

Run: `pyside6-deploy src/json_to_pdf/__main__.py --init`

Expected: `pysidedeploy.spec` exists and `git check-ignore pysidedeploy.spec` exits nonzero because Task 1 unignored it.

- [ ] **Step 2: Make the deployment mode and resources explicit**

Set the generated spec to `standalone` mode, output under `dist/`, and include `src/json_to_pdf/assets/fonts` plus `THIRD_PARTY_NOTICES.md`. Retain only Qt Core, Gui, Widgets, PrintSupport, and Pdf modules discovered from imports. Do not add icons or a wrapper build script.

- [ ] **Step 3: Add the exact OS matrix workflow**

Use `windows-latest`, `macos-14`, and `ubuntu-24.04` with Python 3.12. Each job installs `requirements.lock`, runs the full tests, runs `python -m compileall -q src tests`, builds with `pyside6-deploy -c pysidedeploy.spec`, locates the packaged executable, runs `--smoke-convert tests/fixtures/student-report.json packaged-report.pdf`, and validates that PDF with a short pypdf command. Linux uses the runner's headless Qt configuration.

- [ ] **Step 4: Run local deployment and packaged smoke conversion**

Run: `pyside6-deploy -c pysidedeploy.spec`

Run the resulting executable for the current OS:

- Windows: `dist/json-to-pdf.exe --smoke-convert tests/fixtures/student-report.json dist/smoke-report.pdf`
- macOS: `dist/json-to-pdf.app/Contents/MacOS/json-to-pdf --smoke-convert tests/fixtures/student-report.json dist/smoke-report.pdf`
- Linux: `dist/json-to-pdf.bin --smoke-convert tests/fixtures/student-report.json dist/smoke-report.pdf`

Run: `python -c "from pypdf import PdfReader; r=PdfReader('dist/smoke-report.pdf', strict=True); assert len(r.pages)>0; assert 'Başarılı' in ''.join(p.extract_text() or '' for p in r.pages)"`

Expected: all commands exit 0 and the packaged PDF contains searchable Turkish text.

- [ ] **Step 5: Commit native deployment**

```bash
git add pysidedeploy.spec .github/workflows/release.yml
git commit -m "build: package standalone applications on three systems"
```

### Task 11: Record usage, licensing, and release evidence

**Files:**
- Modify: `README.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `docs/quality-checklist.md`

**Interfaces:**
- Consumes: completed application and OS matrix artifacts
- Produces: honest user/maintainer documentation and a release gate

- [ ] **Step 1: Expand user documentation with exact supported behavior**

Document install/run/build commands, supported OS floors, the five-step GUI workflow, all eight resource limits, UTF-8/object-array policy, supported font repertoire, privacy/offline behavior, literal URL/HTML handling, error categories, accessibility scope, and all v1 non-goals. State explicitly that PDF/UA, universal Unicode, image embedding, and crash durability are not claimed.

- [ ] **Step 2: Record third-party notices and the licensing decision gate**

List Python, PySide6/Qt 6.11.2, pypdf 6.16.1, Nuitka 4.1.1, pytest, pytest-qt, and Noto Sans v2.015 with source links and licenses. Include the complete font OFL in the artifact. Document that community Qt is LGPLv3/GPLv3/commercial-licensed and require the project owner or qualified counsel to approve the chosen release-distribution path; do not present the document as legal advice.

- [ ] **Step 3: Create the cross-platform visual/interoperability checklist**

For each target OS, record artifact SHA-256, test run, packaged smoke result, sample page count, first/last extracted sentinels, font-embedding result, footer sequence, temp-file cleanup, and two named independent PDF viewers. Include checkboxes for no blank/truncated/overlapping page, no horizontal clipping, readable Turkish text, working selection/search, and keyboard GUI workflow.

- [ ] **Step 4: Run the final automated gate**

Run: `python -m pytest -q`

Run: `python -m compileall -q src tests`

Run twice with the same fixture/title/date and assert equal page count plus extracted text. Confirm no test opens a network connection. Wait for all three packaging jobs and complete every quality-checklist row with evidence.

Expected: all commands/jobs pass, every checklist row has evidence, and owner/legal release review is either recorded or remains an explicit release blocker.

- [ ] **Step 5: Commit release documentation**

```bash
git add README.md THIRD_PARTY_NOTICES.md docs/quality-checklist.md
git commit -m "docs: record usage licensing and release acceptance"
```

## Acceptance Traceability

| Requirement | Implementation task and proof |
|---|---|
| Offline Windows/macOS/Linux desktop | Tasks 9–11; packaged OS matrix and smoke conversion |
| Select JSON/output/title, generate, open | Task 9; GUI workflow tests |
| Generic recursive layouts | Tasks 5 and 8; renderer matrix and synthetic representative fixture |
| Exact JSON number semantics | Task 4; lexeme/non-finite/boundary tests |
| Humanized keys and literal escaped values | Task 5; label and adversarial tests |
| Turkish and deterministic font behavior | Tasks 3 and 7; hashes, glyph checks, PDF descriptor proof |
| A4/margins/footer/searchable text | Tasks 6 and 7; geometry, footer, extraction, media-box tests |
| No clipping/blank/truncated/corrupt pages | Tasks 6–8 and 11; adversarial fixtures, QtPdf rasterization, viewer gate |
| No network/resource interpretation | Tasks 5, 8, and 11; active-tag absence and runtime/test network prohibition |
| Stable redacted errors | Tasks 2, 4, 7, and 9; injected secret sentinels at every boundary |
| Exact resource limits | Tasks 2, 4, 7, and 11; at/over tests and user docs |
| Responsive GUI and thread ownership | Task 9; blocked-converter event-loop and cleanup tests |
| Validated replacement preserving prior output | Task 7; real OS filesystem plus failure injection |
| Accessibility without PDF/UA claim | Tasks 5, 9, and 11; heading/type, labels/focus, manual verification |
| Reproducible native deployment and notices | Tasks 1, 10, and 11; pinned lock, standalone artifacts, notices, review gate |

## Final Review Rule

Do not declare implementation complete from unit tests alone. Completion requires all tests, the three-OS standalone package matrix, packaged smoke conversion, strict pypdf read-back, embedded-font proof, QtPdf rasterization, local representative-file conversion, repeat-run text/page stability, two-viewer inspection per OS, temporary-file cleanup proof, and the documented release-licensing decision.
