# 团队同步：Auth / Invite / WebSocket（Ke 更新说明）

本文面向 **Lou（前端）** 与 **Mingtao（AI core / 共享后端）**，说明 Ke 在 app 层落地的能力，以及你们如何 **拉代码后立刻用起来**。技术细节与英文 API 表见 [`AUTH_AND_WEBSOCKET_KE.md`](AUTH_AND_WEBSOCKET_KE.md)。

---

## 1. 这次更新是什么（一句话）

在原有 **HTTP 聊天落库**（`POST /cases/{case_id}/chat/event`、`/chat/messages`）之上，增加了：

- **JWT 注册/登录**（`/auth/register`、`/auth/login`、`/auth/me`）
- **`AUTH_MODE`**：控制是否要求登录 + **case 成员**才能访问 `/cases/*` 与 policy 相关路由
- **Case membership**：创建 case 时若带 Bearer，可将当前用户记为 **owner**
- **Invite**：owner 发邀请码、公开校验、登录用户 **accept-invite** 加入 case
- **WebSocket 房间**：`WS /ws/cases/{case_id}?token=...`，房间内广播 + 可选走与 HTTP 相同的 **AI 派发与落库**（`chat_dispatch`）

**默认行为不变：** 未配置或 `AUTH_MODE=off` 时，现有 demo / smoke / 你们已接好的 HTTP 流程 **无需登录**。

---

## 2. 所有人：拉代码后必做

```bash
cd backend
pip install -e ".[dev]"
```

新增依赖包括：`PyJWT`、`passlib[bcrypt]`、`email-validator`；`bcrypt` 版本已钉在 3.x 以兼容 passlib（见 `pyproject.toml`）。

数据库在下次 **bootstrap**（启动后端且 `DATABASE_URL` 可用）时会自动 **create_all** 新表：`users`、`case_memberships`、`case_invites`（与原有 `cases`、`case_chat_messages` 一起）。

---

## 3. 跑共享后端 / 本机后端的人（常为 Mingtao 或 Ke）

在 **`backend/.env`**（或环境变量）中按需增加：

| 变量 | 建议 |
| --- | --- |
| `JWT_SECRET_KEY` | 若要开放 **注册/登录**，设为 **足够长的随机字符串**；不填则 `/auth/register`、`/auth/login` 返回 **503**。 |
| `AUTH_MODE` | 课程 demo 保持 **`off`**，现有 `run_demo_smoke`、无登录前端 **零改动**。要演示「登录后才能进 case」时再改为 **`required`**（或 **`optional`**）。 |

**CORS：** 与以前一样，用 `CORS_ALLOW_ORIGINS` / `CORS_ALLOW_ORIGIN_REGEX` 允许队友本地前端（如 `http://localhost:3000`）。浏览器请求的 **Origin** 是前端地址，**不是** ngrok 域名。

**ngrok：** 仅把 API base URL 换成当前隧道地址；详见 [`REMOTE_SHARED_BACKEND_ZH.md`](REMOTE_SHARED_BACKEND_ZH.md)。JWT 与 WS 无 ngrok 专用配置。

---

## 4. 给 Lou：前端怎么接

### 4.1 仍可只用 HTTP（推荐先保持）

- 现有 **`POST /cases/{case_id}/chat/messages`**、**`POST /cases/{case_id}/chat/event`**、**`GET /cases/{case_id}/chat/messages`** 行为在 **`AUTH_MODE=off`** 下与之前一致。
- **`GET /cases/{case_id}`** 的 **`room_bootstrap`** 仍可用来展示 pinned 摘要；WS 是 **可选** 实时层。

### 4.2 若要登录 / 成员 / 邀请流程

1. **`POST /auth/register`** 或 **`POST /auth/login`**，保存返回的 **`access_token`**（及 `user` 展示信息）。
2. 需要身份的请求加请求头：  
   **`Authorization: Bearer <access_token>`**
3. **`POST /cases`**：带 Bearer 时，新 case 会把当前用户记为 **owner**（见英文文档「Case ownership」）。
4. **邀请：** owner 调 **`POST /cases/{case_id}/invites`**；被邀请用户登录后 **`POST /auth/accept-invite`**，body：`{"token":"..."}`。
5. **校验邀请（可选 UI）：** **`GET /invites/lookup?token=...`**（无需登录）。

### 4.3 WebSocket

- URL：**`ws://` 或 `wss://`**（与你们站点 HTTP/HTTPS 一致）  
  `.../ws/cases/{case_id}?token=<access_token>`  
  浏览器 WebSocket **不便自定义 Header**，故 token 放在 **query**。
- 消息体 JSON 示例见 [`AUTH_AND_WEBSOCKET_KE.md`](AUTH_AND_WEBSOCKET_KE.md)（`type: chat`、`ping` 等）。
- **`AUTH_MODE=required`** 时，无 token 或无权访问该 case 会 **直接断连**（关闭码见英文文档）。

### 4.4 与 `YI_FRONTEND_API_EXAMPLE_ZH.md` 的关系

该文档里的 policy / accident / chat **HTTP 示例仍然有效**；若产品上要登录，在相同请求上 **叠加 Bearer** 即可。更细的字段表以 **`AUTH_AND_WEBSOCKET_KE.md`** 与 OpenAPI（`/docs`）为准。

---

## 5. 给 Mingtao：AI / 回归 / 共享后端

### 5.1 AI 行为契约 **未改**

- **`handle_chat_event`** 仍在 **`ai/chat/chat_ai_service.py`**；业务入口统一经 **`app/chat_dispatch.py`** 的 **`chat_event_dispatch`**（HTTP 与 WS 共用）。
- **`AI_CHAT_BEHAVIOR_CONTRACT_ZH.md`** 中的触发规则、stage、字段含义 **仍然适用**。

### 5.2 脚本与 CI

- **`scripts/run_chat_ai_eval.py`**、**`scripts/run_demo_smoke.py`**：在共享机 **`AUTH_MODE=off`** 时 **行为与以前一致**（无需改命令行）。
- 本地：**`cd backend && pytest`**；若未装依赖先 **`pip install -e ".[dev]"`**。

### 5.3 数据库与 KB

- 新表与 RAG / 向量表 **并列**，不改变 **policy ingest、ask、accident report** 的数据路径。
- 若你们在共享环境启用 **`AUTH_MODE=required`**，需知：**旧的无 membership 的 case** 在 required 下可能 **403**（文档见英文说明）；demo 建议仍用 **`off`** 或 **新建已登录用户创建的 case**。

---

## 6. 文档与代码索引

| 内容 | 位置 |
| --- | --- |
| 英文 API / 环境变量 / WS 协议 | [`AUTH_AND_WEBSOCKET_KE.md`](AUTH_AND_WEBSOCKET_KE.md) |
| App 层路由总览 | [`BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md`](BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md) |
| 共享 ngrok | [`REMOTE_SHARED_BACKEND_ZH.md`](REMOTE_SHARED_BACKEND_ZH.md) |
| 路由注册 | `backend/main.py` |
| Auth / Invite / WS 路由 | `backend/app/routers/auth.py`、`invites.py`、`ws_chat.py` |

---

## 7. 协作约定（简短）

- **默认 demo：** `AUTH_MODE=off` + 可选不配 `JWT_SECRET_KEY`，全员无需改前端即可联调。
- **要演示登录 + 邀请 + WS：** 共享机配置 `JWT_SECRET_KEY`，Lou 按 §4 接 Bearer + WS；Mingtao确认隧道与 CORS。
- **问题排查：** 先看 **`/health`**、**`AUTH_MODE`**、是否 **`JWT_SECRET_KEY`** 与是否带 **Bearer**。

---

*Ke — Auth / Invite / WebSocket 里程碑同步文档。*
