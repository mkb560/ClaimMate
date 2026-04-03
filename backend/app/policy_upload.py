from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, UploadFile


def sanitize_filename(filename: str | None) -> str:
    original = Path(filename or "policy.pdf").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", original).strip("-.") or "policy.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned


async def save_uploaded_policy(case_id: str, upload: UploadFile, storage_root: Path) -> Path:
    if upload.content_type not in {None, "", "application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    filename = sanitize_filename(upload.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Uploaded file does not look like a PDF.")

    case_dir = storage_root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    destination = case_dir / filename
    destination.write_bytes(content)
    return destination
