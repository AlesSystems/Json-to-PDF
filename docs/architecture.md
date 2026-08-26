# JSON-to-PDF v1 Architecture

## Status

**Implementation status:** implemented and reviewed; release acceptance gates remain.

This design is for a small, offline desktop application that converts one JSON file into a readable, searchable PDF for students. The renderer is generic: `/Users/altanesmer/Desktop/bilisim_questions.json` is representative data, not a schema contract, and every value inside it is treated only as untrusted data.

## Decision

Use Python 3.12 with PySide6/Qt Widgets for the GUI and Qt's own rich-text print pipeline for PDF generation:

```text
JSON bytes -> bounded parser -> typed JSON tree -> escaped Qt rich-text HTML
  -> QTextDocument -> QPrinter(PdfFormat) -> temporary PDF
  -> strict pypdf validation -> same-directory os.replace -> final PDF
```

This is the best v1 option because the same supported Qt stack supplies the cross-platform GUI, rich-text layout, tables, font handling, pagination, threading primitives, PDF creation, and packaged deployment. `QPrinter.PdfFormat` produces searchable PDFs; `QTextDocument` supports headings, lists, tables, repeated `<thead>` rows, line height, and explicit page breaks. It avoids a web server, browser engine, JavaScript runtime, and WeasyPrint's additional Pango/fontconfig packaging surface.

The engine decision reopens only if the checked-in pagination and adversarial-layout fixtures still fail after one bounded Qt layout correction. At that gate, compare WeasyPrint and ReportLab using the same fixtures; do not mix engines inside v1.

## Alternatives considered

- **WeasyPrint:** stronger CSS paged-media support and a good fallback, but additional native dependencies complicate three-OS desktop packaging.
- **ReportLab:** precise low-level PDF control, but wrapping, tables, rich text, and pagination would become application-owned layout code.
- **Browser/web application:** easy modern styling, but adds a browser/server runtime, a larger attack surface, and less deterministic offline packaging.
- **Schema-specific report template:** prettier for the sample, but fails the generic-JSON requirement.

## Supported platforms and pinned baseline

- CPython 3.12.
- PySide6 6.11.2.
- pypdf 6.16.1.
- pytest 9.1.1 and pytest-qt 4.5.0 for development.
- Nuitka 4.1.1 through `pyside6-deploy` for deployment.
- Windows 10/11 x86-64.
- macOS 13+ universal2.
- Linux x86-64 with glibc 2.34+.

Exact versions live in `requirements.lock`. Release artifacts are built natively on each OS; cross-compilation is not supported.

## Product scope

The GUI lets the user:

1. select one `.json` file;
2. select a `.pdf` destination;
3. optionally set a document title;
4. generate the PDF without freezing the GUI; and
5. explicitly open the successfully generated result.

V1 is offline and contains no telemetry, network access, URL fetching, cloud service, accounts, database, web server, browser preview, template editor, theming system, plugin system, batch conversion, or image decoding. URLs, file-looking text, and HTML-looking strings are rendered literally. V1 does not claim tagged PDF or PDF/UA conformance.

## Global limits and input policy

```python
@dataclass(frozen=True)
class ResourceLimits:
    max_file_bytes: int = 20 * 1024 * 1024
    max_depth: int = 32
    max_nodes: int = 200_000
    max_string_chars: int = 100_000
    max_number_chars: int = 1_000
    max_title_chars: int = 200
    max_pages: int = 2_000
    max_pdf_bytes: int = 250 * 1024 * 1024
```

- Input is UTF-8; a UTF-8 BOM is accepted with `utf-8-sig`.
- The top level must be a non-empty object or array. Scalar and empty roots are rejected with a clear policy error.
- Root depth is 1. Node count includes every JSON value, including containers and the root; object keys are not separate nodes.
- `JsonNumber(str)` stores the parser-supplied numeric lexeme. `json.loads` uses it for both `parse_int` and `parse_float`, so long integers, decimal precision, signs, and exponent notation are not converted through binary float. `parse_constant` rejects `NaN`, `Infinity`, and `-Infinity` as invalid JSON.
- Standard decoder failures retain one-based line and column. Rejected non-standard numeric constants use a safe locationless message because the standard callback does not expose their position.
- The input filename stem is the default title. Whitespace-only titles fall back to that stem; longer titles are rejected.
- The source filename, not its full path, appears in the document.

## Unicode and font contract

Bundle the exact Google Fonts Noto Sans v2.015 variable font before renderer or PDF work:

| Asset | Source | SHA-256 |
|---|---|---|
| `src/json_to_pdf/assets/fonts/NotoSans[wdth,wght].ttf` | Google Fonts commit `6a003b5eb672dc8bf5bff5937cf5863f8b175445`, `ofl/notosans/NotoSans[wdth,wght].ttf` | `bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d` |
| `src/json_to_pdf/assets/fonts/OFL.txt` | same commit, `ofl/notosans/OFL.txt` | `cee9892f9f0cc8fe882c9e9537ee6a89621d86ee7ceaf70b02e2b2b1c25c061a` |

The app registers the font before starting conversion workers. Registration returning `-1`, an unexpected family, or a hash mismatch is a startup error. `QRawFont.supportsCharacter()` checks every unique printable code point from generated labels, title, filename, keys, and string values. Tabs/newlines are allowed whitespace; unsupported printable code points and unsupported control characters cause a safe `UnsupportedCharacterError` naming only `U+XXXX`, never the source value.

This makes v1 reliable for the font's covered repertoire, including Turkish, Latin, Greek, and Cyrillic. It deliberately does not claim all-Unicode coverage. Additional script fonts are a future, test-driven extension.

PDF tests inspect the page font descriptors for an embedded `/FontFile`, `/FontFile2`, or `/FontFile3`; merely enabling font embedding is not accepted as proof.

## Component boundaries

Product code lives in `src/json_to_pdf/`; tests live in `tests/`.

### `errors.py`

Defines `ConversionError` and typed subclasses for input read, invalid JSON, policy, resource limit, unsupported character, render, PDF validation, and output write failures. Each class exposes a stable `public_message`; internal exceptions are chained as causes. Public messages never include JSON values, exception text, or full filesystem paths.

### `limits.py`

Owns `ResourceLimits` and `DEFAULT_LIMITS`. No environment-variable or user-configurable limit system exists in v1.

### `model.py`

```python
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

### `font.py`

```python
FONT_FAMILY = "Noto Sans"

def register_bundled_font() -> str: ...
def require_supported_text(texts: Iterable[str]) -> None: ...
```

Font registration happens once in the GUI thread before any conversion worker starts. Glyph checking is deterministic and performs no fallback to an unbundled system font.

### `loader.py`

```python
def load_json(path: Path, limits: ResourceLimits = DEFAULT_LIMITS) -> LoadedDocument: ...
```

`load_json` checks existence/readability and byte size, reads once, decodes with `utf-8-sig`, parses with bounded `JsonNumber` callbacks, rejects constants/scalar/empty roots, then uses an explicit stack to enforce depth, value-node, key/value-string, and number-length limits.

### `render.py`

```python
@dataclass(frozen=True)
class RenderContext:
    title: str
    source_name: str
    generated_on: date

def humanize_key(key: str) -> str: ...
def render_html(value: dict[str, JsonValue] | list[JsonValue], context: RenderContext) -> str: ...
```

`render_html` is pure. All keys, strings, title, and filename are escaped with `html.escape(..., quote=True)`. It emits no anchors, image tags, scripts, external styles, or resource URLs. Numeric lexemes are emitted only from validated `JsonNumber` values.

Adaptive rules are deterministic:

1. Scalar object fields become two-column definition rows.
2. A homogeneous array of objects becomes a table only when every row has the same scalar fields, the table has at most four columns, every cell is at most 60 characters, and the sum of per-column maximum lengths is at most 120 characters.
3. All other object arrays become numbered record cards.
4. Primitive arrays become ordered lists.
5. Nested objects/arrays become titled sections.
6. Mixed arrays become numbered sections.
7. Key labels split camelCase, snake_case, and kebab-case; values and key order remain semantically unchanged.

Tables use `<thead>` for repeated printed headers. The PDF stage sets `QTextOption.WrapAtWordBoundaryOrAnywhere`, constrains the document/table to the body width, and tests an unbroken 80-character token. Cards may split across pages because Qt does not document `page-break-inside`; the acceptance rule is readable continuation without clipping, not keep-together.

### `pdf.py`

```python
@dataclass(frozen=True)
class PdfMetadata:
    title: str
    source_name: str
    generated_on: date

@dataclass(frozen=True)
class PdfValidationResult:
    page_count: int
    extracted_text: tuple[str, ...]

def validate_pdf(
    path: Path,
    *,
    expected_title: str,
    expected_source_name: str,
    limits: ResourceLimits = DEFAULT_LIMITS,
) -> PdfValidationResult: ...

def write_pdf_atomic(
    html_text: str,
    destination: Path,
    metadata: PdfMetadata,
    limits: ResourceLimits = DEFAULT_LIMITS,
) -> PdfValidationResult: ...
```

The writer creates a closed, unique temporary file beside the destination. It configures A4 portrait with 18 mm margins and 72 DPI so device coordinates correspond to PDF points. Within the printable rectangle it reserves a 7 mm footer band and 3 mm gap; the remaining rectangle is the body.

Pagination is a first-class proof, not an assumption:

1. Create `QTextDocument`, set the registered font, `WrapAtWordBoundaryOrAnywhere`, printer paint device, zero internal margin, and page size equal to the body rectangle.
2. Force layout, read `M = document.pageCount()`, and reject `M == 0` or `M > max_pages` before painting.
3. Require `QPainter.begin(printer)`.
4. For page index `i`, set `PaintContext.clip` to that document-page rectangle; translate the painter to the printable body origin and by `-i * body_height`; draw the document; restore; draw `Page i+1 of M` only in the footer band.
5. Call and check `printer.newPage()` before pages 2..M only, never after page M. Require `QPainter.end()`.

The painter, document, and printer are created, used, and destroyed in the same worker thread. No widgets are touched there.

Before extraction, runtime validation rejects an oversized PDF and excessive page count. `PdfReader(..., strict=True)` must open an unencrypted document. Every content page must yield non-empty bounded text; title and source-name sentinels must be found. Fixture-specific sentinels belong in integration tests, not the runtime API.

All reader/file handles close before replacement. Only after validation does `os.replace(temp, destination)` run. Failure removes the temporary file and leaves a prior destination unchanged. Same-directory replacement is atomic where the OS guarantees it; the design does not claim crash durability. Real-filesystem behavior is exercised on all target OS runners, including a Windows locked-destination failure; mocks are reserved for deterministic injected failures.

### `service.py`

```python
def convert(
    request: ConversionRequest,
    *,
    limits: ResourceLimits = DEFAULT_LIMITS,
    generated_on: date | None = None,
) -> PdfValidationResult: ...
```

`convert` is the synchronous boundary: load, select title, check supported text, render, write, validate, and return the page count/text receipt. The GUI invokes it in a Qt worker object on `QThread` and receives queued success/failure signals.

### `gui.py` and `__main__.py`

```python
class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None: ...

def main(argv: Sequence[str] | None = None) -> int: ...
```

The minimal window contains labeled source, destination, and title fields; browse buttons; Generate and Open Result actions; visible status; and an error dialog. Generate is disabled while work runs. Labels have buddies and accessible names, focus order follows the workflow, and every control is keyboard-operable. Open Result is explicit and uses `QDesktopServices.openUrl()` after conversion success.

`__main__.py` also accepts an internal `--smoke-convert SOURCE DESTINATION` path used only by packaged CI to prove that the deployed binary contains its font and can convert a fixture. It calls the same service and is not a second conversion implementation.

## PDF quality and accessibility gate

Automated acceptance requires:

- strict, unencrypted, parseable PDF with 1..2,000 pages;
- A4 portrait media boxes and 18 mm margins;
- correct `Page N of M` sequence with no blank trailing page or footer/body overlap;
- title, source name, Turkish text, first-record and final-record fixture sentinels extractable/searchable;
- non-empty extracted text for every content page;
- embedded Noto Sans font descriptor;
- no annotations or external resources from HTML/URL-looking input;
- no horizontal clipping for wide tables, long Turkish prose, cards, and unbroken tokens;
- prior destination unchanged and no sibling temporary PDF after every injected failure;
- repeat runs with fixed input/date/tool versions produce the same page count and extracted text (byte identity is not required);
- rasterization of every page with `PySide6.QtPdf.QPdfDocument.render()` produces nonblank body content;
- recorded inspection in two independent viewers on each OS before release.

Accessibility scope is honest: logical H1/H2/H3 order, at least 10 pt body text, dark text on white, 135% line height, selectable/searchable text, descriptive GUI labels, keyboard focus order, visible progress, and actionable errors. Tagged PDF and PDF/UA are non-goals.

## Packaging and licensing

`pyside6-deploy -c pysidedeploy.spec` builds `standalone` artifacts so Qt libraries remain separate rather than statically fused. `.gitignore` must explicitly unignore `pysidedeploy.spec`. The spec includes the font and license assets; unspecified icons and build-wrapper scripts are excluded.

CI uses `windows-latest`, `macos-14`, and `ubuntu-24.04`, runs unit/integration tests, builds on that OS, runs the packaged `--smoke-convert`, and validates the resulting PDF. Only after validation, CI archives the final native app/output directory and uploads it with a SHA-256 manifest and the validated PDF receipt. Release artifacts include `THIRD_PARTY_NOTICES.md`, the font OFL, and applicable Qt/PySide6/pypdf/Python notices.

Qt community packages are LGPLv3/GPLv3/commercial-licensed, while PySide6 also lists a GPLv2 alternative. Nuitka is AGPLv3 with its stated runtime exception. The implementation must document the selected distribution path and obtain project-owner or qualified-counsel review of release packaging; this architecture records engineering gates and is not legal advice.

## Primary references

- [Qt for Python](https://doc.qt.io/qtforpython-6/)
- [Qt rich-text HTML subset](https://doc.qt.io/qt-6/richtext-html-subset.html)
- [Qt Print Support](https://doc.qt.io/qtforpython-6/PySide6/QtPrintSupport/index.html)
- [QPrinter searchable PDF mode](https://doc.qt.io/qtforpython-6/PySide6/QtPrintSupport/QPrinter.html)
- [Qt threading support](https://doc.qt.io/qt-6.10/threads-modules.html)
- [`pyside6-deploy`](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html)
- [Python `json`](https://docs.python.org/3/library/json.html)
- [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)
- [pypdf `PdfReader`](https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html)
- [Noto Sans v2.015 source metadata](https://github.com/google/fonts/tree/6a003b5eb672dc8bf5bff5937cf5863f8b175445/ofl/notosans)
