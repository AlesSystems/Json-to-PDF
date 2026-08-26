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


def test_validated_application_is_archived_hashed_and_uploaded_with_pdf_receipt() -> None:
    validation = WORKFLOW.index("Validate packaged PDF")
    archive = WORKFLOW.index("Archive validated application")
    manifest = WORKFLOW.index("Create SHA-256 manifest")
    upload = WORKFLOW.index("actions/upload-artifact@v4")
    assert validation < archive < manifest < upload
    assert "dist/json-to-pdf-arm64.app" not in WORKFLOW[archive:]
    assert "dist/json-to-pdf-x86_64.app" not in WORKFLOW[archive:]
    assert "packaged-report.pdf" in WORKFLOW[upload:]
    assert "artifact-sha256.txt" in WORKFLOW[upload:]
    assert "$GITHUB_STEP_SUMMARY" in WORKFLOW[manifest:upload]
    archive_contract = WORKFLOW[archive:manifest]
    assert "json-to-pdf-windows-x86_64.tar.gz" in archive_contract
    assert ".zip" not in archive_contract
    assert "tar -a" not in archive_contract
    assert archive_contract.count('tar -czf "$archive"') == 1
