# JSON-to-PDF Planning Loop Record

**Status:** `success`

## Loop contract

**Goal:** Choose the smallest high-quality architecture and produce an implementation-ready, test-driven plan for an offline generic JSON-to-PDF desktop application.

**Signal:** Every v1 requirement maps to a defined interface, failing-first test, pass signal, commit boundary, packaging proof, and honest release gate; a fresh reviewer finds no unresolved blocker.

**Move:** Inspect representative data -> compare supported engines -> choose -> draft with Sol low -> attack with Sol high -> incorporate accepted findings -> verify artifacts -> stop.

**Proof:** Structural sample profile; official Qt/Python/pypdf/Noto sources; three planning documents; independent review; deterministic scans for placeholders/signature drift; Git diff checks.

**Stop:**

- `success`: revised documents pass primary self-audit and no implementation work remains in this planning scope.
- `blocked`: a required fact, authority, or user decision prevents a safe plan.
- `exhausted`: the compared stacks cannot meet the v1 acceptance contract within scope.
- `stagnated`: two consecutive revise/review passes repeat the same unresolved objection without new evidence.

## Authority and budget

Authorized work was limited to reading the repository/sample, official-source research, one GPT-5.6 Sol low planning worker, one GPT-5.6 Sol high read-only reviewer, and writing `docs/`. Product code, dependency installation, commits, pushes, publishing, and release decisions were outside scope.

The bounded loop used one worker draft, one reviewer pass, and one primary revision. Reviewer output is evidence, not acceptance authority; the primary agent independently checks factual contradictions and the final artifacts.

## Baseline evidence

- Repository at `b1be9f5`: `.gitignore`, `LICENSE`, and a two-line `README.md`; no product code or tests.
- Sample: `/Users/altanesmer/Desktop/bilisim_questions.json`.
- Sample SHA-256: `fd44809a6cb70829e95fe99137a944f599944e559b5cc098673046d6696fcfa2`.
- Valid minified JSON, 23,981 bytes, top-level object with `correctCount`, `message`, `passed`, `score`, `subjectAnalysis`, `totalQuestions`, and `wrongAnswers`.
- Recursive shape: 71 objects, 2 arrays, 275 string values, 77 numbers, 204 nulls, and one boolean.
- `subjectAnalysis`: 2 shallow four-field records.
- `wrongAnswers`: 68 long-text records; `userAnswerImage`, `correctAnswerImage`, and `solution` are null in all 68.
- Maximum string length: 246 characters.
- 229 of 275 string values contain at least one non-ASCII code point, counted with regex `[^\x00-\x7F]`. Object keys are excluded from this count.

Every sample value was treated as data only. No instruction-like string was followed or executed.

## Architecture comparison

| Option | Fit | Decision |
|---|---|---|
| Python + PySide6 + `QTextDocument`/`QPrinter` | One supported cross-platform stack for GUI, rich text, pagination, searchable PDF, threading, and deployment | **Selected** |
| Python + WeasyPrint | Strong paged CSS; extra Pango/fontconfig/native packaging surface | Fallback after a checked-in Qt conformance failure |
| Python + ReportLab | Fine-grained PDF control; application must own wrapping/tables/pagination | Rejected for v1 complexity |
| Browser/web app | Modern CSS; larger runtime/attack surface and weaker offline desktop fit | Rejected |

Primary evidence:

- <https://doc.qt.io/qtforpython-6/>
- <https://doc.qt.io/qt-6/richtext-html-subset.html>
- <https://doc.qt.io/qtforpython-6/PySide6/QtPrintSupport/index.html>
- <https://doc.qt.io/qtforpython-6/PySide6/QtPrintSupport/QPrinter.html>
- <https://doc.qt.io/qt-6.10/threads-modules.html>
- <https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html>
- <https://docs.python.org/3/library/json.html>
- <https://docs.python.org/3/library/os.html#os.replace>
- <https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html>

## Delegated stages

### 1. Sol low planning worker

**Result:** `success` as a draft. It created the three requested files and passed its own placeholder/interface/diff scan.

**Primary verification:** files existed and were non-empty; `git diff --check` passed; the explicit placeholder scan was clean. However, the later independent review correctly found format-level and semantic gaps that the worker's narrow scan did not detect.

### 2. Sol high reviewer

**Verdict:** `REJECTED` for implementation readiness, while explicitly approving the core Qt architecture.

Material findings:

1. mandatory implementation-plan format and task granularity missing;
2. font asset unresolved and sequenced after PDF consumers;
3. pagination/footer geometry underspecified;
4. eight-column/80-character table threshold unsafe for A4 portrait;
5. default float parsing/non-standard constants violate the numeric contract;
6. runtime PDF sentinel requirements contradict function signatures;
7. versions/platform/deployment/licensing constraints incomplete;
8. real per-OS replacement tests not separated from injected failures;
9. error redaction incomplete;
10. Poppler dependency unowned;
11. sample non-ASCII count inaccurate.

### 3. Primary contradiction checks

| Disputed claim | Smallest re-check | Verdict |
|---|---|---|
| Sample has 257 vs 229 non-ASCII string values | `jq` with `[^\x00-\x7F]` plus independent `rg` count | Reviewer correct: 229; the original `\u` regex was mis-specified |
| Noto asset/version/hashes | Downloaded exact files from Google Fonts commit and ran SHA-256 | Reviewer correct; hashes match the revised architecture |
| Repeated table headers | Qt supported rich-text documentation for `<thead>` | Original capability correct; Qt repeats `<thead>` while printing |
| Card keep-together/page-break-inside | Qt documented CSS property list | Reviewer correct; not documented, so keep-together claim removed |
| Worker-thread PDF generation | Qt threading and rich-text reentrancy documentation | Architecture correct when each worker owns its instances and widgets remain on GUI thread |
| Same-directory replacement | Python `os.replace` documentation | Correct primitive; POSIX atomic guarantee is documented, Windows must be exercised in its real OS lane |

## Incorporated corrections

- Rewrote `docs/implementation-plan.md` to the mandatory header/task/files/interfaces/TDD/commit format.
- Pinned Python, PySide6, pypdf, pytest, pytest-qt, Nuitka, OS floors, CI runners, and standalone deployment.
- Selected exact Noto Sans v2.015 font/OFL assets with verified hashes and moved typography before rendering/PDF.
- Added a glyph-repertoire gate and removed the unsupported all-Unicode implication.
- Added number lexemes, non-finite rejection, and numeric/title/page/PDF limits.
- Replaced the table rule with at most four columns plus bounded widths and wrap-anywhere.
- Specified the pagination geometry, clipping/translation sequence, checked painter/new-page/end results, and no-final-`newPage()` rule.
- Reconciled strict production validation with metadata-derived sentinels; fixture sentinels remain integration tests.
- Added real OS filesystem proof, Windows lock behavior, and separate failure injection.
- Replaced Poppler with QtPdf rasterization; removed wrapper build script and unspecified icons.
- Added full error-redaction coverage and corrected the sample statistic.
- Added an explicit owner/legal release gate rather than claiming LGPL compliance from engineering checks.

## Implementation gate

Implementation may begin only after the project owner reviews `docs/architecture.md` and `docs/implementation-plan.md`. During execution:

1. complete tasks in order because later interfaces depend on earlier contracts;
2. do not begin general PDF work until the pagination proof passes;
3. do not release from unit tests alone;
4. reopen the engine decision only on the documented conformance-failure gate; and
5. do not publish artifacts until the licensing/distribution decision is recorded.

The plan authorizes no implementation, commit, push, or release by itself.

## Final verification receipt

Primary verification passed on 2026-08-26:

- all three files exist and contain 1,384 lines / 67,703 bytes before this receipt update;
- the implementation plan has the required header, 11 tasks, 11 interface blocks, 66 checkbox steps, 11 coherent commit boundaries, and 15 acceptance mappings;
- placeholder, trailing-whitespace, code-fence, and untracked diff checks are clean;
- all public interfaces named by the architecture appear in the implementation plan;
- every material reviewer blocker is traceably incorporated;
- the sample SHA-256 and corrected 229-string non-ASCII count match deterministic commands;
- both Noto asset hashes match the pinned Google Fonts files; and
- `git status --short` reports only the new `docs/` directory.

**Stop:** `success` for planning. Product implementation, commits, publishing, and the release-licensing decision remain deliberately unclaimed and require separate authority.
