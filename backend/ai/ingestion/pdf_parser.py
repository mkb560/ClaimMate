from __future__ import annotations

from io import BytesIO

import pdfplumber
from pypdf import PdfReader

from ai.ingestion.types import ParsedPage


def _escape_markdown_cell(text: str) -> str:
    return text.replace("|", r"\|")


def _table_to_markdown(table: list[list[str | None]]) -> str:
    cleaned_rows: list[list[str]] = []
    for row in table:
        cleaned_rows.append([_escape_markdown_cell((cell or "").strip()) for cell in row])

    if not cleaned_rows or not cleaned_rows[0]:
        return ""

    header = cleaned_rows[0]
    separator = ["---"] * len(header)
    body = cleaned_rows[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def parse_pdf_bytes(pdf_bytes: bytes) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    reader = PdfReader(BytesIO(pdf_bytes))

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text_parts: list[str] = []
            raw_text = page.extract_text() or ""
            if raw_text.strip():
                text_parts.append(raw_text.strip())
            else:
                fallback_text = (reader.pages[index - 1].extract_text() or "").strip()
                if fallback_text:
                    text_parts.append(fallback_text)

            for table in page.extract_tables() or []:
                markdown = _table_to_markdown(table)
                if markdown:
                    text_parts.append(markdown)

            pages.append(ParsedPage(page_num=index, text="\n\n".join(text_parts).strip()))

    if any(page.text for page in pages):
        return pages

    fallback_pages: list[ParsedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        fallback_pages.append(
            ParsedPage(
                page_num=index,
                text=(page.extract_text() or "").strip(),
            )
        )
    return fallback_pages
