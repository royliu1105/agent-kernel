"""Document parser primitives for RAG ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}
SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


class ParserError(ValueError):
    """Raised when document bytes cannot be parsed."""


class UnsupportedDocumentError(ParserError):
    """Raised when no parser supports the document input."""


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    parser_name: str
    content_char_count: int


class TextMarkdownParser:
    name = "text-markdown"

    def can_parse(self, *, filename: str | None, mime_type: str | None) -> bool:
        normalized_mime = (mime_type or "").split(";")[0].strip().lower()
        if normalized_mime in SUPPORTED_TEXT_MIME_TYPES:
            return True
        if filename is None:
            return False
        return Path(filename).suffix.lower() in SUPPORTED_TEXT_EXTENSIONS

    def parse(
        self,
        *,
        content: bytes,
        filename: str | None = None,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        if not self.can_parse(filename=filename, mime_type=mime_type):
            raise UnsupportedDocumentError(
                "Only text/plain and text/markdown documents are supported."
            )

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ParserError("Document is not valid UTF-8 text.") from error

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return ParsedDocument(
            text=normalized,
            parser_name=self.name,
            content_char_count=len(normalized),
        )
