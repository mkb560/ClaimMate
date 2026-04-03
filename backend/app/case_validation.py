from __future__ import annotations

import re

from fastapi import HTTPException

CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_case_id(case_id: str) -> str:
    if not CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(
            status_code=400,
            detail="case_id may contain only letters, numbers, underscores, and hyphens.",
        )
    return case_id
