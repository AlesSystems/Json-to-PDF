import json
from pathlib import Path

from json_to_pdf.errors import (
    InputReadError,
    InvalidJsonError,
    PolicyError,
    ResourceLimitError,
)
from json_to_pdf.limits import DEFAULT_LIMITS, ResourceLimits
from json_to_pdf.model import JsonNumber, JsonValue, LoadedDocument


def load_json(
    path: Path, limits: ResourceLimits = DEFAULT_LIMITS
) -> LoadedDocument:
    try:
        if path.stat().st_size > limits.max_file_bytes:
            raise ResourceLimitError()
        raw = path.read_bytes()
    except ResourceLimitError:
        raise
    except (OSError, ValueError) as error:
        raise InputReadError(cause=error) from error

    if len(raw) > limits.max_file_bytes:
        raise ResourceLimitError()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidJsonError(cause=error) from error

    def number(token: str) -> JsonNumber:
        if len(token) > limits.max_number_chars:
            raise ResourceLimitError()
        return JsonNumber(token)

    def constant(token: str) -> None:
        raise InvalidJsonError(nonstandard_constant=token)

    def object_value(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for key, item in pairs:
            if key in result:
                raise PolicyError()
            result[key] = item
        return result

    try:
        value = json.loads(
            text,
            parse_int=number,
            parse_float=number,
            parse_constant=constant,
            object_pairs_hook=object_value,
        )
    except json.JSONDecodeError as error:
        raise InvalidJsonError(line=error.lineno, column=error.colno) from error
    except RecursionError as error:
        if _max_container_depth(text) > limits.max_depth:
            raise ResourceLimitError(cause=error) from error
        raise InvalidJsonError(cause=error) from error

    if not isinstance(value, (dict, list)) or not value:
        raise PolicyError()
    _validate_tree(value, limits)
    return LoadedDocument(value=value, source_name=path.name)


def _max_container_depth(text: str) -> int:
    depth = maximum = 0
    in_string = escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            maximum = max(maximum, depth)
        elif character in "]}":
            depth -= 1
    return maximum


def _validate_tree(value: JsonValue, limits: ResourceLimits) -> None:
    stack = [(value, 1)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > limits.max_depth or count > limits.max_nodes:
            raise ResourceLimitError()

        if isinstance(item, dict):
            for key, child in item.items():
                if len(key) > limits.max_string_chars:
                    raise ResourceLimitError()
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, JsonNumber):
            if len(item) > limits.max_number_chars:
                raise ResourceLimitError()
        elif isinstance(item, str) and len(item) > limits.max_string_chars:
            raise ResourceLimitError()
