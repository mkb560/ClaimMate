from __future__ import annotations

from pathlib import Path

from app.paths import LOCAL_POLICY_STORAGE_ROOT


def ensure_policy_storage_ready() -> tuple[bool, str | None, Path]:
    root = LOCAL_POLICY_STORAGE_ROOT
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, None, root
    except Exception as exc:
        return False, str(exc), root
