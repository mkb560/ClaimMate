# Technical Milestone 4 Video Script

## 开场

Script（英文旁白）:

Hi, I’m Mingtao Ding, and this is Technical Milestone 4 for ClaimMate.

In Milestone 3, I showed authenticated users, case ownership, invite creation, and case-aware AI chat.

In Milestone 4, I’m focusing on a more stable collaborative claim workflow. I’ll show five main updates: user-specific case list, invite link generation, shared case context with accident photos, persistent chat history, and a WebSocket room smoke test.

## 录制地址

使用 Railway 云端后端：

```text
https://claimmate-backend-production.up.railway.app/docs
```

建议使用新的 demo 数据，避免邮箱或 case 重复：

```text
owner email: owner.tm4.20260424.7@example.com
password: ClaimMate123
case_id: tm4-full-20260424-7
```

如果重录，把 `.5` 和 `-5` 换成新的数字。

## 录制前快速准备

这部分是 Milestone 3 的基础，只需要快速做完，不用重点讲。

### 准备 1：注册 owner

接口：

```text
POST /auth/register
```

请求体：

```json
{
  "email": "owner.tm4.20260424.7@example.com",
  "password": "ClaimMate123",
  "display_name": "Mingtao Owner"
}
```

操作：

- 复制返回的 `access_token`
- 点击 Swagger 右上角 `Authorize`
- 粘贴 owner token

### 准备 2：创建 case

接口：

```text
POST /cases
```

请求体：

```json
{
  "case_id": "tm4-full-20260424-7"
}
```

### 准备 3：seed accident demo

接口：

```text
POST /cases/{case_id}/demo/seed-accident
```

路径参数：

```text
tm4-full-20260424-7
```

Script（英文旁白）:

First, I quickly set up the owner case. I register the owner, create a case, and seed a prepared accident context.

This setup reuses the Milestone 3 foundation. Now I’ll focus on what is new in Milestone 4.

## 展示点 1：用户自己的 Case List

接口：

```text
GET /cases
```

使用：

- owner token

重点展示：

- `cases`
- `case_id`
- `role`
- `created_at`

Script（英文旁白）:

The first Milestone 4 update is the user-specific case list.

Here I’m calling `GET /cases` as the owner. The backend returns only the cases that belong to the current authenticated user.

This is used by the frontend “Your Cases” page, so users no longer see a shared global list. Each user sees only their own claim workspace.

## 展示点 2：创建 Invite Link

接口：

```text
POST /cases/{case_id}/invites
```

路径参数 `case_id` 填：

```text
tm4-full-20260424-7
```

请求体：

```json
{
  "role": "member",
  "expires_in_hours": 168
}
```

重点展示：

- `case_id`
- `token`
- `role`
- `expires_at`

Script（英文旁白）:

The second update is invite link generation.

As the owner, I can create an invite for this case. The response includes the case ID, invite token, role, and expiration time.

This is the backend foundation for bringing another participant into the same claim workspace. I’m not going to manually accept the invite in this short recording, but the generated token is what the frontend invite flow uses.

## 展示点 3：共享 Case Context 和事故照片

### 3A：读取 case snapshot

接口：

```text
GET /cases/{case_id}
```

路径参数：

```text
tm4-full-20260424-7
```

使用：

- owner token

重点展示：

- `stage_a`
- `stage_b`
- `report_payload`
- `chat_context`
- `room_bootstrap`

Script（英文旁白）:

Now I’m reading the case snapshot.

The response includes accident intake data, generated report payload, chat-ready context, and room bootstrap.

This is the shared case context that can be used by the report page, chat page, and future invited participants.

### 3B：上传事故照片

接口：

```text
POST /cases/{case_id}/incident-photos
```

路径参数：

```text
tm4-full-20260424-7
```

表单填写：

- `file`: 选择一张小的 JPG、PNG 或 WEBP 图片
- `category`: `owner_damage`
- `caption`: `rear bumper damage demo`
- `taken_at`: 留空

重点展示：

- `photo_attachment.photo_id`
- `photo_attachment.storage_key`
- `stage_a.photo_attachments`

Script（英文旁白）:

The third update is accident photo persistence.

I upload a photo to the same case. The backend validates the image, stores it, and appends photo metadata into Stage A.

This makes accident photos part of the case record instead of only local frontend previews.

可选补充：

如果时间够，可以再调用：

```text
GET /cases/{case_id}/incident-photos/{photo_id}
```

展示图片可以通过 `photo_id` 取回。

## 展示点 4：持久化 Case Chat

### 4A：发送 chat message

接口：

```text
POST /cases/{case_id}/chat/messages
```

路径参数：

```text
tm4-full-20260424-7
```

请求体：

```json
{
  "message_text": "@AI what deadlines should I know for this claim?",
  "sender_role": "owner",
  "invite_sent": true,
  "participants": [
    {
      "user_id": "owner-1",
      "role": "owner"
    },
    {
      "user_id": "adjuster-1",
      "role": "adjuster"
    }
  ]
}
```

重点展示：

- `response.trigger`
- `response.metadata.stage`
- `response.metadata.deadline_intent`
- `response.text`

Script（英文旁白）:

The fourth update is persistent case chat.

Here I send an `@AI` deadline question in the case chat. The backend uses the saved case dates and returns a deadline explainer inside the shared case context.

This keeps the Milestone 2 AI behavior, but now it runs inside a product-style case chat workflow.

### 4B：读取 chat history

接口：

```text
GET /cases/{case_id}/chat/messages
```

路径参数：

```text
tm4-full-20260424-7
```

重点展示：

- `messages`
- user row
- AI row
- `ai_payload`
- `created_at`

Script（英文旁白）:

Now I load the chat history.

The user message and the AI response are both stored in the case timeline.

So the system is no longer only returning one-off AI responses. It now has a persistent shared conversation history.

## 展示点 5：WebSocket Room Smoke Test

这部分用终端展示。

云端命令：

```bash
cd backend
./.venv/bin/python scripts/run_collab_smoke.py --base-url https://claimmate-backend-production.up.railway.app --timeout 180
```

重点展示：

- `"passed": true`
- `accept_invite`
- `post_chat_messages`
- `websocket`
- `ready_type`
- `pong_type`
- `user1_type`
- `user2_type`
- `ai1_type`
- `ai2_type`

Script（英文旁白）:

The fifth update is the WebSocket room prototype.

For the video, I’m using an automated smoke test instead of manually accepting the invite in Swagger. The smoke test creates two users, creates a case, accepts an invite, sends a chat message, and opens two WebSocket clients to the same case room.

The output shows `ready`, `pong`, user message broadcast, and AI message broadcast.

This is still an in-memory prototype, but it proves the core real-time collaboration path.

## 结尾

Script（英文旁白）:

That completes Technical Milestone 4.

Compared with Milestone 3, ClaimMate now supports a fuller collaborative workflow: users can list their own cases, generate invite links, access shared accident context, save photos into the case, persist chat history, and verify live WebSocket communication with an end-to-end smoke test.

Together with the earlier policy Q&A, accident context, deadline explainer, and dispute support, ClaimMate is now much closer to a real AI-powered claims copilot.
