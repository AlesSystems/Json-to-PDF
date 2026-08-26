from dataclasses import dataclass


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


DEFAULT_LIMITS = ResourceLimits()
