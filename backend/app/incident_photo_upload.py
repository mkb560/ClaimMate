from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_BYTES = 10 * 1024 * 1024


def _sanitize_stem(filename: str | None) -> str:
    original = Path(filename or "photo").stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", original).strip("-.") or "photo"
    return cleaned[:64]


def _resolve_extension(content_type: str | None, filename: str | None) -> str:
    if content_type in _ALLOWED_CONTENT_TYPES:
        return f".{_ALLOWED_CONTENT_TYPES[content_type]}"
    suffix = Path(filename or "").suffix.lower()
    if suffix in _ALLOWED_EXTENSIONS:
        return ".jpg" if suffix == ".jpeg" else suffix
    raise HTTPException(status_code=400, detail="Unsupported image type. Use JPG, PNG, or WEBP.")


def _validate_magic_bytes(content: bytes) -> None:
    is_jpeg = content.startswith(b"\xff\xd8\xff")
    is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_webp):
        raise HTTPException(status_code=400, detail="Uploaded file does not look like a valid image.")


async def save_incident_photo(case_id: str, upload: UploadFile, storage_root: Path) -> tuple[str, str]:
    ext = _resolve_extension(upload.content_type, upload.filename)
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded file is too large (max 10MB).")
    _validate_magic_bytes(content)

    photo_id = uuid4().hex
    stem = _sanitize_stem(upload.filename)
    filename = f"{photo_id}-{stem}{ext}"

    case_dir = storage_root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    destination = case_dir / filename
    destination.write_bytes(content)
    storage_key = f"{case_id}/{filename}"
    return photo_id, storage_key
