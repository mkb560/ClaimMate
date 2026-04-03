from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOCAL_POLICY_STORAGE_ROOT = BACKEND_ROOT / ".local_data" / "policies"
