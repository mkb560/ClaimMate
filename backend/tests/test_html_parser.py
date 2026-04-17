from ai.ingestion.html_parser import parse_html_bytes


def test_parse_html_bytes_omits_page_number_for_html_sources() -> None:
    pages = parse_html_bytes(b"<html><body><h1>Title</h1><p>Body</p></body></html>")

    assert len(pages) == 1
    assert pages[0].page_num is None
    assert "Title" in pages[0].text
