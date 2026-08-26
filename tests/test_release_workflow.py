from pathlib import Path


WORKFLOW = Path(".github/workflows/release.yml").read_text(encoding="utf-8")


def test_pull_requests_run_release_matrix() -> None:
    assert "  pull_request:\n" in WORKFLOW


def test_macos_build_composes_and_proves_universal2_artifact() -> None:
    assert 'lipo -archs "$(command -v python)"' in WORKFLOW
    ordered = [
        "arch -arm64 pyside6-deploy -c pysidedeploy.spec",
        "arch -x86_64 pyside6-deploy -c pysidedeploy.spec",
        "lipo -create",
        "lipo -archs \"$file\"",
    ]
    positions = [WORKFLOW.index(fragment) for fragment in ordered]
    assert positions == sorted(positions)
    assert WORKFLOW.count("grep -qw arm64") >= 2
    assert WORKFLOW.count("grep -qw x86_64") >= 2


def test_macos_normalizes_and_verifies_signature_before_smoke() -> None:
    clear = WORKFLOW.index("xattr -cr dist/json-to-pdf.app")
    sign = WORKFLOW.index("codesign --force --deep --sign - dist/json-to-pdf.app")
    remove_after_sign = WORKFLOW.index(
        "xattr -d com.apple.FinderInfo dist/json-to-pdf.app 2>/dev/null || true",
        sign,
    )
    verify = WORKFLOW.index("codesign --verify --deep --strict dist/json-to-pdf.app")
    smoke = WORKFLOW.index("Run packaged smoke conversion")
    assert clear < sign < remove_after_sign < verify < smoke
