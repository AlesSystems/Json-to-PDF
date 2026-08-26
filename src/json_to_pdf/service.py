import os
from collections.abc import Iterable
from datetime import date

from .errors import PolicyError, ResourceLimitError
from .font import require_supported_text
from .limits import DEFAULT_LIMITS, ResourceLimits
from .loader import load_json
from .model import ConversionRequest, JsonNumber, JsonValue
from .pdf import PdfMetadata, PdfValidationResult, write_pdf_atomic
from .render import RenderContext, render_html


def convert(
    request: ConversionRequest,
    *,
    limits: ResourceLimits = DEFAULT_LIMITS,
    generated_on: date | None = None,
) -> PdfValidationResult:
    try:
        source = request.source.resolve(strict=False)
        destination = request.destination.resolve(strict=False)
        if source == destination:
            raise PolicyError()
        if source.exists() and destination.exists() and os.path.samefile(
            source, destination
        ):
            raise PolicyError()
    except (OSError, ValueError, RuntimeError) as error:
        raise PolicyError(cause=error) from error
    document = load_json(request.source, limits)
    title = (
        request.title.strip()
        if request.title and request.title.strip()
        else request.source.stem
    )
    if len(title) > limits.max_title_chars:
        raise ResourceLimitError()
    require_supported_text(
        [title, document.source_name, *_iter_keys_and_strings(document.value)]
    )
    context = RenderContext(title, document.source_name, generated_on or date.today())
    html_text = render_html(document.value, context)
    metadata = PdfMetadata(title, document.source_name, context.generated_on)
    return write_pdf_atomic(html_text, request.destination, metadata, limits)


def _iter_keys_and_strings(root: JsonValue) -> Iterable[str]:
    stack = [root]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            yield from value.keys()
            stack.extend(reversed(tuple(value.values())))
        elif isinstance(value, list):
            stack.extend(reversed(value))
        elif isinstance(value, str) and not isinstance(value, JsonNumber):
            yield value
