# Final fix wave report

## Implemented contracts

- The shared `convert()` boundary now rejects normalized source/destination equality and existing-file aliases via `os.path.samefile`. It raises the existing redacted `PolicyError` before loading or rendering, so the input bytes cannot be replaced by a PDF.
- PDF painting now treats QPrinter's non-full-page paint device as a printable-origin coordinate system. Body and footer rectangles start at `(0, 0)` relative to that origin, producing one physical 18 mm margin, a 7 mm footer band, and a 3 mm body/footer gap.
- Font startup hashes the bytes obtained through `importlib.resources` against `bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d` before any QFontDatabase registration. Read and integrity failures leave `_raw_font` unset.
- Release CI archives the exact final app/output directory only after packaged PDF validation, writes a SHA-256 manifest and step summary, and uploads the archive, manifest, and `packaged-report.pdf` through `actions/upload-artifact@v4`. The macOS archive names only `dist/json-to-pdf.app`, excluding both thin intermediate bundles.
- `MainWindow` accepts an optional QWidget parent and passes it to QMainWindow. Architecture status and licensing gates now match the implemented/reviewed product, PySide's GPLv2 alternative, and Nuitka's AGPLv3/runtime-exception notice without legal advice.

## TDD evidence

RED tests were written and run before production changes.

```text
tests/test_service.py exact path + hardlink alias: 2 failed, DID NOT RAISE PolicyError
tests/test_font.py modified readable font: failed after addApplicationFont was reached
tests/test_gui.py parent ownership: failed, __init__ accepted no parent
tests/test_pagination.py physical positions: failed; body content x=102 pt (36 mm), footer baseline x=543 pt after transforms
tests/test_release_workflow.py artifact receipt: failed, archive step absent
```

The first Qt RED attempt aborted because macOS had reapplied `UF_HIDDEN` to ignored Qt plug-ins. Clearing that local flag (no repository change) made each behavioral failure reproducible.

GREEN focused command:

```text
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_service.py tests/test_font.py tests/test_pdf.py tests/test_pagination.py tests/test_gui.py tests/test_release_workflow.py
64 passed, 2 skipped in 1.21s
```

The real generated PDF exposes body x=51 pt (~18 mm), footer baseline x=491.875 pt, body baseline y=780.3125 pt, and footer baseline y=57.046875 pt on the 595 x 842 pt A4 media box. The footer occupies the intended physical 18-25 mm bottom band; body pagination reserves the 7 mm band plus 3 mm gap. Text extraction, pagination, and Noto embedding remain covered.

## Full verification

```text
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
118 passed, 2 skipped in 1.20s

.venv/bin/python -m compileall -q src tests
exit 0

ruby -e "require 'yaml'; YAML.load_file('.github/workflows/release.yml')"
yaml: PASS

QT_QPA_PLATFORM=offscreen JSON_TO_PDF_SAMPLE=tests/fixtures/student-report.json .venv/bin/python -m pytest -q -m sample
1 passed, 119 deselected in 0.11s

QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m json_to_pdf --smoke-convert tests/fixtures/student-report.json <temporary>/source-smoke.pdf
exit 0

production convert() twice, fixed date/title/input
reproducibility: PASS; pages=2; extracted_chars=1188

git diff --check
exit 0
```

The pinned upstream OFL trailing space remains untouched and is the accepted upstream exception. The 100 MB standalone bundle was not rebuilt; native archive/upload execution remains evidence for the three-OS CI matrix. No push, PR, release, or legal decision was performed.

## Self-review

The implementation uses only stdlib path identity, hashing, archiving helpers already present on runners, and existing application error types. No new abstraction or dependency was added. Workflow-derived paths are passed through environment variables or quoted shell variables; no untrusted glob or expression is executed.
