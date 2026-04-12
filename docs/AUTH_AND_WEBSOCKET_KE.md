# Auth, invites, and WebSocket rooms (Ke — implementation notes)

This document describes the **app-layer authentication**, **case membership + invite tokens**, and **WebSocket chat rooms** added for ClaimMate’s product path beyond raw HTTP chat persistence. It complements [`plan.md`](plan.md) and [`PROJECT_PROGRESS_AND_STRUCTURE.md`](PROJECT_PROGRESS_AND_STRUCTURE.md).

## Configuration (`.env`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `AUTH_MODE` | `off` | `off`: no access checks (demo/smoke). `optional`: Bearer optional; if present, user must be a **case member** when the case already has memberships. `required`: Bearer **required** for all `/cases/*` and WS; user must be a member (see below). |
| `JWT_SECRET_KEY` | empty | Required to issue/verify JWTs. If unset, `/auth/register` and `/auth/login` return **503**; clients can still use the API in `AUTH_MODE=off`. |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm. |
| `JWT_EXPIRES_MINUTES` | `10080` (7d) | Access token lifetime (see `ai/config.py` field `jwt_expires_minutes`). |

**Demo / `run_demo_smoke.py`:** keep `AUTH_MODE=off` (or unset) so existing unauthenticated flows keep working.

**Stricter environments:** set `JWT_SECRET_KEY` to a long random string, register a user, create cases **with** `Authorization: Bearer <token>`, then use invites for additional users.

## Data model

New SQLAlchemy tables on the same `CaseBase` metadata as `cases` (created on `bootstrap_vector_store`):

- **`users`** — email (unique), bcrypt `password_hash`, optional `display_name`.
- **`case_memberships`** — `(case_id, user_id, role)` with unique `(case_id, user_id)`. Roles used: `owner`, `member`, `viewer` (invite default `member`).
- **`case_invites`** — one-time invite rows: `token_hash` (SHA-256 of the secret token), `role`, `expires_at`, optional `created_by_user_id`.

Deleting a case removes related memberships and invites (`ON DELETE CASCADE` / explicit deletes in `delete_case_and_related_data`).

## HTTP API

### Auth

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/auth/register` | Body: `email`, `password` (min 8 chars), optional `display_name`. Returns `access_token`, `token_type`, `user`. Needs `JWT_SECRET_KEY`. |
| `POST` | `/auth/login` | Body: `email`, `password`. Same response shape as register. |
| `GET` | `/auth/me` | Requires `Authorization: Bearer`. |

### Case ownership

- **`POST /cases`** — If the client sends a valid Bearer token, the user is recorded as **`owner`** on the new case **when** the case has no memberships yet (first owner only).

### Invites

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/cases/{case_id}/invites` | Authenticated; **only `owner`** membership can create. Response includes a one-time `token` and `expires_at`. Body: optional `role`, `expires_in_hours` (1–720). |
| `GET` | `/invites/lookup?token=...` | Public. Returns `case_id`, `role`, `expires_at`, `valid` (not expired). |
| `POST` | `/auth/accept-invite` | Body: `{ "token": "..." }`. Requires Bearer. Adds membership and consumes the invite. |

### Case access rules (`AUTH_MODE`)

- **`off`:** Same as before: no membership checks on `/cases/*` or policy routes.
- **`optional`:** Unauthenticated requests still allowed. If a Bearer is sent, the user must satisfy membership rules for cases that already have members.
- **`required`:** Every `/cases/*` and policy route that takes a `case_id` requires a valid JWT. The user must be in `case_memberships` for that case. Cases with **zero** memberships (legacy anonymous cases) return **403** with an explanatory message — recreate the case while authenticated or stay on `AUTH_MODE=off` for legacy demos.

## WebSocket: `WS /ws/cases/{case_id}`

- **URL:** `ws://<host>/ws/cases/{case_id}?token=<JWT>` (query param; browsers rarely send custom headers on WebSocket upgrade).
- **Auth:** Same membership rules as HTTP when `AUTH_MODE` is `optional` or `required`. Invalid/missing token when required → connection closed (custom codes `4401` / `4403` / `4404`).
- **Protocol:** JSON text frames.
  - `{"type":"ping"}` → `{"type":"pong"}`.
  - `{"type":"chat","message_text":"...","sender_role":"owner","invite_sent":false,"participants":[...],"run_ai":true}` — broadcasts a `user_message` to the room; if `run_ai` is true (default), runs the same **`chat_event_dispatch`** path as HTTP (persists user + AI rows when applicable) and broadcasts `ai_message` with the AI payload.
- **Rooms:** In-memory `CaseRoomManager` (prototype). Horizontal scaling would need a shared pub/sub layer; documented as a known limitation.

## Code layout

| Area | Files |
| --- | --- |
| Password + JWT | `app/auth_core.py` |
| Users, memberships, invites | `app/auth_service.py` |
| `Depends` + `AuthContext` | `app/auth_deps.py` |
| Case access checks | `app/case_access.py` |
| Shared AI chat dispatch | `app/chat_dispatch.py` (used by HTTP routers + WS) |
| Routers | `app/routers/auth.py`, `invites.py`, `ws_chat.py` |
| Room fan-out | `app/ws_room_manager.py` |
| ORM | `models/auth_orm.py` |
| Metadata bootstrap | `ai/runtime.py` imports `models.auth_orm` so tables are created with `CaseBase.metadata.create_all` |

## Dependencies

`pyproject.toml` adds: `PyJWT`, `passlib[bcrypt]`, `email-validator` (for `EmailStr` on register/login).

After pulling, reinstall: `cd backend && pip install -e '.[dev]'`.

---

*Last updated with this auth/WS milestone (Ke).*
