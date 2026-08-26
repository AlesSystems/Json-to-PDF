# Release Quality Checklist

Complete one row per native target. `Pending` is a release blocker, not a failure waiver. Attach CI run/artifact links when available; never copy evidence between operating systems.

## Automated and packaged evidence

| Target | Artifact SHA-256 | Test run | Packaged smoke | Pages | First / last extracted sentinel | Embedded Noto Sans | Footer sequence | Temp cleanup |
|---|---|---|---|---:|---|---|---|---|
| Windows 10/11 x86-64 | **Pending: PR artifact** | **Pending: PR CI** | **Pending: PR CI** | — | **Pending** | **Pending** | **Pending** | **Pending, including locked destination** |
| macOS 13+ universal2 | **Pending: universal2 PR artifact**. Local arm64 executable: `97a9e886d7ebefafc4cef1c16513ced4cba155d0e60129478cf5d8c18890c77d` | Local macOS arm64: `112 passed, 2 skipped` | Local arm64: pass, strict pypdf; universal2 execution **pending PR CI** | 2 | Fixed-date production run: first `Fixed report`; last `SON-KAYIT-İŞARETİ-8` | Local automated tests: pass | Local automated tests: `Page 1 of 2`, `Page 2 of 2` | Local automated success/failure tests: pass |
| Linux x86-64, glibc 2.34+ | **Pending: PR artifact** | **Pending: PR CI** | **Pending: PR CI** | — | **Pending** | **Pending** | **Pending** | **Pending** |

## Independent viewer and interaction inspection

Viewer names are fixed for reproducibility; version, tester, date, and notes must be entered for each completed inspection.

### Windows — Microsoft Edge and Adobe Acrobat Reader

- Evidence: **Pending**
- [ ] No blank, truncated, or overlapping page
- [ ] No horizontal clipping
- [ ] Turkish text is readable
- [ ] Text selection and search work
- [ ] Full GUI workflow works by keyboard

### macOS — Preview and Adobe Acrobat Reader

- Evidence: **Pending** (no manual two-viewer inspection has been performed)
- [ ] No blank, truncated, or overlapping page
- [ ] No horizontal clipping
- [ ] Turkish text is readable
- [ ] Text selection and search work
- [ ] Full GUI workflow works by keyboard

### Linux — Evince and Okular

- Evidence: **Pending**
- [ ] No blank, truncated, or overlapping page
- [ ] No horizontal clipping
- [ ] Turkish text is readable
- [ ] Text selection and search work
- [ ] Full GUI workflow works by keyboard

## Release decisions

- [ ] Windows, macOS universal2, and Linux pull-request matrix jobs passed and their immutable run links are recorded.
- [ ] Every automated row above contains OS-specific evidence.
- [ ] Both named viewers were inspected on every OS and every checkbox is complete.
- [ ] Project owner or qualified counsel approved and recorded the Qt/PySide6 distribution path.

**Current status: blocked for release.** Windows/Linux packaged evidence, macOS universal2 PR execution, every two-viewer/manual inspection, and the licensing decision remain pending. Local macOS arm64 evidence is useful engineering proof but is not a substitute for those gates.
