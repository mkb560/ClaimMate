from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    KB_A = "kb_a"
    KB_B = "kb_b"


@dataclass(slots=True)
class ParsedPage:
    page_num: int
    text: str
    section: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChunkPayload:
    source_type: SourceType
    chunk_text: str
    page_num: int | None
    section: str | None
    case_id: str | None = None
    document_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmbeddedChunk:
    source_type: SourceType
    chunk_text: str
    embedding: list[float]
    page_num: int | None
    section: str | None
    case_id: str | None = None
    document_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

