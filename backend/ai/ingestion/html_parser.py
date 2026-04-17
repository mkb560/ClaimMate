from __future__ import annotations

import html2text

from ai.ingestion.types import ParsedPage


def parse_html_bytes(html_bytes: bytes) -> list[ParsedPage]:
    parser = html2text.HTML2Text()
    parser.ignore_links = True
    parser.ignore_images = True
    parser.ignore_tables = False
    parser.body_width = 0

    try:
        decoded = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        decoded = html_bytes.decode("utf-8", errors="replace")

    text = parser.handle(decoded).strip()
    return [ParsedPage(page_num=None, text=text)]
