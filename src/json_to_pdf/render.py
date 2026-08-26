import re
from dataclasses import dataclass
from datetime import date
from html import escape

from .font import FONT_FAMILY
from .model import JsonScalar, JsonValue


@dataclass(frozen=True)
class RenderContext:
    title: str
    source_name: str
    generated_on: date


def humanize_key(key: str) -> str:
    label = re.sub(r"[_-]+", " ", key)
    label = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", label)
    return label[:1].upper() + label[1:]


def _is_scalar(value: JsonValue) -> bool:
    return not isinstance(value, (dict, list))


def _scalar_text(value: JsonScalar) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _is_table(records: list[dict[str, JsonValue]]) -> bool:
    if not records or any(list(row) != list(records[0]) for row in records[1:]):
        return False
    keys = list(records[0])
    if len(keys) > 4 or any(
        not _is_scalar(value) for row in records for value in row.values()
    ):
        return False
    widths = [max(len(_scalar_text(row[key])) for row in records) for key in keys]
    return max(widths, default=0) <= 60 and sum(widths) <= 120


def _append_object(parts: list[str], value: dict[str, JsonValue], level: int) -> None:
    scalars = [(key, item) for key, item in value.items() if _is_scalar(item)]
    if scalars:
        parts.append('<table class="definition">')
        for key, item in scalars:
            parts.extend(
                (
                    "<tr><th>",
                    escape(humanize_key(key), quote=True),
                    "</th><td>",
                    escape(_scalar_text(item), quote=True),
                    "</td></tr>",
                )
            )
        parts.append("</table>")
    for key, item in value.items():
        if not _is_scalar(item):
            heading = min(level, 3)
            parts.extend(
                (
                    f"<h{heading}>",
                    escape(humanize_key(key), quote=True),
                    f"</h{heading}>",
                )
            )
            _append_value(parts, item, level + 1)


def _append_records(
    parts: list[str], records: list[dict[str, JsonValue]], level: int
) -> None:
    if _is_table(records):
        keys = list(records[0])
        parts.append('<table class="records"><thead><tr>')
        for key in keys:
            parts.extend(("<th>", escape(humanize_key(key), quote=True), "</th>"))
        parts.append("</tr></thead><tbody>")
        for row in records:
            parts.append("<tr>")
            for key in keys:
                parts.extend(
                    ("<td>", escape(_scalar_text(row[key]), quote=True), "</td>")
                )
            parts.append("</tr>")
        parts.append("</tbody></table>")
        return
    for number, record in enumerate(records, 1):
        parts.extend(
            (
                '<div class="record-card">',
                f"<h{min(level, 3)}>Record {number}</h{min(level, 3)}>",
            )
        )
        _append_object(parts, record, level + 1)
        parts.append("</div>")


def _append_array(parts: list[str], value: list[JsonValue], level: int) -> None:
    if value and all(isinstance(item, dict) for item in value):
        _append_records(parts, value, level)  # type: ignore[arg-type]
    elif all(_is_scalar(item) for item in value):
        parts.append("<ol>")
        for item in value:
            parts.extend(
                ("<li>", escape(_scalar_text(item), quote=True), "</li>")  # type: ignore[arg-type]
            )
        parts.append("</ol>")
    else:
        for number, item in enumerate(value, 1):
            heading = min(level, 3)
            parts.append(f"<h{heading}>Item {number}</h{heading}>")
            _append_value(parts, item, level + 1)


def _append_value(parts: list[str], value: JsonValue, level: int) -> None:
    if isinstance(value, dict):
        _append_object(parts, value, level)
    elif isinstance(value, list):
        _append_array(parts, value, level)
    else:
        parts.extend(("<p>", escape(_scalar_text(value), quote=True), "</p>"))


def render_html(
    value: dict[str, JsonValue] | list[JsonValue], context: RenderContext
) -> str:
    parts = [
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>",
        f"body {{ font-family: '{FONT_FAMILY}'; font-size: 10pt; color: #202124; }}",
        "h1 { font-size: 20pt; } h2 { font-size: 15pt; } h3 { font-size: 12pt; }",
        "table { border-collapse: collapse; width: 100%; margin-bottom: 10px; }",
        "th, td { border: 1px solid #c7c7c7; padding: 5px; vertical-align: top; }",
        "th { background-color: #eeeeee; text-align: left; }",
        ".definition th { width: 32%; }",
        ".record-card { border: 1px solid #aaaaaa; margin: 8px 0; padding: 8px; }",
        "</style></head><body><h1>",
        escape(context.title, quote=True),
        "</h1><p>Source: ",
        escape(context.source_name, quote=True),
        "<br>Generated: ",
        escape(context.generated_on.isoformat(), quote=True),
        "</p>",
    ]
    _append_value(parts, value, 2)
    parts.append("</body></html>")
    return "".join(parts)
