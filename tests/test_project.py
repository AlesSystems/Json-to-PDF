from importlib.metadata import version


def test_pinned_runtime_versions() -> None:
    assert version("PySide6") == "6.11.2"
    assert version("pypdf") == "6.16.1"
