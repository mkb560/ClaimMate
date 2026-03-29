from __future__ import annotations

import html2text

from ai.ingestion.types import ParsedPage


def parse_html_bytes(html_bytes: bytes) -> list[ParsedPage]:
    parser = html2text.HTML2Text()
    parser.ignore_links = True
    parser.ignore_images = True
    parser.ignore_tables = False
    parser.body_width = 0

    text = parser.handle(html_bytes.decode("utf-8", errors="ignore")).strip()
    return [ParsedPage(page_num=1, text=text)]

