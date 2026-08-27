class ConversionError(Exception):
    public_message = "The conversion could not be completed."

    def __init__(self, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(self.public_message)


class InputReadError(ConversionError):
    public_message = "The JSON file could not be read."


class InvalidJsonError(ConversionError):
    public_message = "The JSON is invalid."

    def __init__(
        self,
        line: int | None = None,
        column: int | None = None,
        *,
        nonstandard_constant: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        if line is not None and column is not None:
            self.public_message = (
                f"The JSON is invalid at line {line}, column {column}."
            )
        elif nonstandard_constant is not None:
            self.public_message = "The JSON contains a non-standard numeric constant."
        super().__init__(cause)


class PolicyError(ConversionError):
    public_message = "The JSON does not meet the input policy."


class ResourceLimitError(ConversionError):
    public_message = "The JSON exceeds a resource limit."


class UnsupportedCharacterError(ConversionError):
    def __init__(self, codepoint: int, cause: Exception | None = None) -> None:
        self.public_message = f"The document contains unsupported character U+{codepoint:04X}."
        super().__init__(cause)


class RenderError(ConversionError):
    public_message = "The document could not be rendered."


class PdfValidationError(ConversionError):
    public_message = "The generated PDF is invalid."


class OutputWriteError(ConversionError):
    public_message = "The PDF file could not be written."
