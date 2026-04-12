from __future__ import annotations

from fastapi import HTTPException

from app.auth_deps import AuthContext
from app.auth_service import count_case_members, is_case_member


async def assert_can_access_case(case_id: str, ctx: AuthContext) -> None:
    """Enforce AUTH_MODE rules for case-scoped reads and writes."""
    if ctx.mode == "off":
        return

    if ctx.mode == "required":
        if ctx.user is None:
            raise HTTPException(status_code=401, detail="Authentication required.")
        n = await count_case_members(case_id)
        if n == 0:
            raise HTTPException(
                status_code=403,
                detail="Case has no membership records. Use AUTH_MODE=off for legacy demo access, "
                "or recreate the case while authenticated.",
            )
        if not await is_case_member(case_id, ctx.user.id):
            raise HTTPException(status_code=403, detail="Not a member of this case.")
        return

    # optional
    if ctx.user is None:
        return
    n = await count_case_members(case_id)
    if n == 0:
        return
    if not await is_case_member(case_id, ctx.user.id):
        raise HTTPException(status_code=403, detail="Not a member of this case.")


async def assert_can_create_case(ctx: AuthContext) -> None:
    if ctx.mode == "required" and ctx.user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
