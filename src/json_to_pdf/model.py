from dataclasses import dataclass
from pathlib import Path


class JsonNumber(str):
    pass


JsonScalar = bool | str | JsonNumber | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class LoadedDocument:
    value: dict[str, JsonValue] | list[JsonValue]
    source_name: str


@dataclass(frozen=True)
class ConversionRequest:
    source: Path
    destination: Path
    title: str | None = None
