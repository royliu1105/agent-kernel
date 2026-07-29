import pytest
from kernel_rag import ParserError, TextMarkdownParser, UnsupportedDocumentError


def test_text_markdown_parser_parses_utf8_markdown() -> None:
    parser = TextMarkdownParser()

    parsed = parser.parse(
        content=b"# Deploy\r\n\nShip carefully.\n",
        filename="deploy.md",
        mime_type="text/markdown",
    )

    assert parsed.parser_name == "text-markdown"
    assert parsed.text == "# Deploy\n\nShip carefully.\n"
    assert parsed.content_char_count == len(parsed.text)


def test_text_markdown_parser_supports_plain_text_extension() -> None:
    parser = TextMarkdownParser()

    parsed = parser.parse(content=b"hello", filename="notes.txt", mime_type=None)

    assert parsed.text == "hello"


def test_text_markdown_parser_rejects_unsupported_type() -> None:
    parser = TextMarkdownParser()

    with pytest.raises(UnsupportedDocumentError):
        parser.parse(content=b"%PDF", filename="doc.pdf", mime_type="application/pdf")


def test_text_markdown_parser_rejects_invalid_utf8() -> None:
    parser = TextMarkdownParser()

    with pytest.raises(ParserError):
        parser.parse(content=b"\xff", filename="notes.md", mime_type="text/markdown")
