from importlib import import_module
from importlib.metadata import version


def test_src_package_is_importable() -> None:
    assert import_module("json_to_pdf").__name__ == "json_to_pdf"


def test_pinned_runtime_versions() -> None:
    assert version("PySide6") == "6.11.2"
    assert version("pypdf") == "6.16.1"
