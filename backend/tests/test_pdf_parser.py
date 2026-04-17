from types import SimpleNamespace

from ai.ingestion import pdf_parser


def test_table_to_markdown_escapes_pipes() -> None:
    markdown = pdf_parser._table_to_markdown([["A|B", "C"], ["1|2", "3"]])

    assert r"A\|B" in markdown
    assert r"1\|2" in markdown


def test_parse_pdf_bytes_uses_pypdf_fallback_per_page(monkeypatch) -> None:
    class _FakePdfPlumberPage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self):
            return self._text

        def extract_tables(self):
            return []

    class _FakePdfPlumberDoc:
        pages = [_FakePdfPlumberPage("Page one text"), _FakePdfPlumberPage("")]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeReaderPage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self):
            return self._text

    monkeypatch.setattr(pdf_parser.pdfplumber, "open", lambda *_args, **_kwargs: _FakePdfPlumberDoc())
    monkeypatch.setattr(
        pdf_parser,
        "PdfReader",
        lambda *_args, **_kwargs: SimpleNamespace(pages=[_FakeReaderPage("ignored"), _FakeReaderPage("Page two fallback")]),
    )

    pages = pdf_parser.parse_pdf_bytes(b"%PDF-1.4 fake")

    assert pages[0].text == "Page one text"
    assert pages[1].text == "Page two fallback"
