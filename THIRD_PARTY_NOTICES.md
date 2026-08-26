# Third-Party Notices

This engineering inventory is not legal advice and does not approve a release. Versions are the locked project baseline in `requirements.lock`, `pyproject.toml`, and the font hash contract.

| Component | Locked version | License | Authoritative source and license |
|---|---:|---|---|
| Python | 3.12.x | Python Software Foundation License 2.0 | [Source](https://www.python.org/downloads/source/) · [License](https://docs.python.org/3.12/license.html) |
| PySide6 / Qt for Python | 6.11.2 | LGPLv3 / GPLv2 / GPLv3 / commercial choice | [Source](https://code.qt.io/cgit/pyside/pyside-setup.git/) · [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html) |
| Qt | 6.11.2 | LGPLv3 / GPLv2 / GPLv3 / commercial choice; terms vary by module | [Source](https://code.qt.io/cgit/qt/) · [Qt licensing](https://www.qt.io/licensing/open-source-lgpl-obligations) |
| pypdf | 6.16.1 | BSD 3-Clause | [Source](https://github.com/py-pdf/pypdf/tree/6.16.1) · [License](https://github.com/py-pdf/pypdf/blob/6.16.1/LICENSE) |
| Nuitka | 4.1.1 | AGPLv3; generated target code uses the Nuitka Runtime Library Exception 1.0 | [Source](https://github.com/Nuitka/Nuitka/tree/4.1.1) · [AGPLv3 license](https://github.com/Nuitka/Nuitka/blob/4.1.1/LICENSE.txt) · [Runtime exception](https://github.com/Nuitka/Nuitka/blob/4.1.1/LICENSE-RUNTIME.txt) |
| pytest | 9.1.1 | MIT | [Source](https://github.com/pytest-dev/pytest/tree/9.1.1) · [License](https://github.com/pytest-dev/pytest/blob/9.1.1/LICENSE) |
| pytest-qt | 4.5.0 | MIT | [Source](https://github.com/pytest-dev/pytest-qt/tree/4.5.0) · [License](https://github.com/pytest-dev/pytest-qt/blob/4.5.0/LICENSE) |
| Noto Sans | v2.015, Google Fonts commit `6a003b5eb672dc8bf5bff5937cf5863f8b175445` | SIL Open Font License 1.1 | [Source](https://github.com/google/fonts/tree/6a003b5eb672dc8bf5bff5937cf5863f8b175445/ofl/notosans) · [License](src/json_to_pdf/assets/fonts/OFL.txt) |

The complete, unmodified Noto Sans OFL is packaged at `json_to_pdf/assets/fonts/OFL.txt`; its locked SHA-256 is `cee9892f9f0cc8fe882c9e9537ee6a89621d86ee7ceaf70b02e2b2b1c25c061a`.

## Qt distribution decision gate

Community Qt/PySide6 is offered under LGPLv3, GPLv2, and GPLv3 terms, with commercial licensing also available; terms vary by module. Nuitka itself is AGPLv3, while its Runtime Library Exception 1.0 grants additional permission for qualifying generated target code. Before distributing any standalone artifact, the project owner or qualified counsel must choose and approve the applicable release-distribution paths, verify the obligations for every packaged Qt module/library and for Nuitka plus its runtime exception, and record those decisions in the release evidence. Until then, licensing approval is an explicit release blocker. Nothing in this notice asserts compliance or substitutes for legal advice.
