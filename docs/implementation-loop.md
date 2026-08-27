# Durable Implementation Loop

This is the readable operating record for the 11-task implementation, distilled from the SDD progress ledger.

## Contract

- **Goal:** implement the approved offline JSON-to-PDF architecture through all 11 ordered tasks.
- **Signal:** each task's focused tests pass, a fresh review accepts spec compliance and quality, and the branch passes end-to-end release proof.
- **Move:** brief → failing contract where required → smallest implementation → deterministic checks → independent review → bounded repair/re-review → next task.
- **Budget:** one implementer at a time, at most five repair rounds per task, one final fix wave, and at most three active agents besides the controller.
- **Authority:** feature-worktree edits, tests, coherent commits, feature-branch push, and PR creation are in scope. Merge, deployment, publishing, legal approval, and destructive cleanup of user work are not.
- **Stop:** `PR_READY` only after clean proof and PR creation; `blocked` when required authority/dependency is unavailable; `exhausted` at the repair cap; `stagnated` after two no-progress review cycles.

## Milestones and evidence

| Milestone | Work accepted | Evidence |
|---:|---|---|
| 0% | Architecture and 11-task plan approved | `docs/architecture.md`, `docs/implementation-plan.md`, planning-loop review record |
| 25% | Tasks 1–3: package contract, limits/errors, bundled font | task reports, focused RED/GREEN commits, clean reviews through `1c7c869` |
| 50% | Tasks 4–6: bounded loader, escaped renderer, pagination proof | task reports and repair reviews through `e5e37fd` |
| 75% | Tasks 7–9: validated atomic output, service, accessible GUI | task reports and clean reviews through `559cfe8` |
| 91% | Task 10: deployment spec and three-OS matrix | `4ddc2f1`, `9a50912`, `c093196`; local arm64 package proof; review clean |
| 100% implementation scope | Task 11: usage/notices/checklist/PR trigger and local verification | Task 11 report and commits; implementation-scope completion is distinct from release readiness |

Each task has a brief, implementer report, coherent commit range, focused/full test evidence, and task-level review evidence in `.superpowers/sdd/implementation-plan/`; bounded repairs are recorded in the same ledger.

## Controller rulings

1. **Task 10 could create the initial notice asset; Task 11 owns its audit.** Packaging needed the resource before the documentation task. Cost if wrong: one file appeared one task earlier than its original file list.
2. **Keep the standard-library JSON decoder and product depth ceiling of 32.** Do not mutate process-global recursion state or replace the decoder for out-of-policy custom limits. Cost if wrong: a caller cannot raise depth beyond CPython's safe decoder ceiling.
3. **Bound cleanup retries when a filesystem permanently refuses unlink.** Raise a redacted output error and disclose that a hostile/broken filesystem may leave one temporary PDF. Cost if wrong: that residual file requires manual cleanup.

## Current `PR_READY` gates

`PR_READY` is established by a clean whole-branch review result, a pushed pull request, passing Windows/macOS/Linux PR jobs, universal2 execution proof, complete OS-specific artifact/checklist receipts, two named-viewer inspections per OS, and owner/qualified-counsel Qt and Nuitka distribution decisions.

No merge, deployment, release publication, legal approval, PDF/UA conformance, universal Unicode coverage, crash durability, or cross-platform manual acceptance is claimed by this record.

## Final-system hardening record

Whole-system review identified four boundary defects after the task-level loops: source/destination aliases could destroy input data, QPrinter printable-origin coordinates were counted twice, font bytes were not authenticated at runtime, and CI did not retain a hashed packaged artifact receipt. The bounded final fix wave added fail-closed path-identity inspection (including normalized equality, hardlinks, symlinks, malformed paths, and inspection errors), corrected the PDF body/footer coordinate model, verified the pinned Noto Sans SHA-256 before registration, and archived each validated native output as a permission-preserving `.tar.gz` with a SHA-256 manifest and validated PDF receipt. It also restored QWidget parent ownership and synchronized architecture/licensing wording.

The resulting local proof baseline is `121 passed, 2 skipped` under offscreen Qt, plus successful source compilation, workflow YAML parsing, representative sample conversion, source smoke conversion, two-run page/text reproducibility, and whitespace diff checking. Physical A4 evidence places body text at approximately 51 pt (18 mm) from the left edge and the footer baseline inside the 18–25 mm bottom band, with a 7 mm footer and 3 mm reserved gap. Native Windows/Linux archives and universal2 execution remain three-OS CI evidence; packaging was not rebuilt merely to exercise source-only corrections.
