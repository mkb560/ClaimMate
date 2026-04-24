# Technical Milestone 3 Video Script

## 开场

Hi, I’m Mingtao Ding, and this is Milestone 3 for me.

In Milestone 2, I showed policy question answering, structured accident data, generated report payloads, and stage-aware AI support for deadlines and disputes.

In Milestone 3, I build on that foundation and show what was added after Milestone 2: authenticated case ownership, invite-based case collaboration, persistent chat history, and a real-time room prototype for multi-party claim communication.

## 操作 + Script

推荐这次仍然以 FastAPI Swagger 页面为主录制，必要时补一个很短的终端片段来展示 WebSocket。

先打开：

- 本地后端：`http://127.0.0.1:8000/docs`
- 如果你平时把 `8000` 跑在 demo 模式（`AUTH_MODE=off`），建议单独起一条 auth-enabled 本地后端，例如：`http://127.0.0.1:8010/docs`
- 如果你想用 shared backend，也可以换成对应的 `.../docs`

这次录制前，建议确认本地后端配置成：

- `AUTH_MODE=required`
- `JWT_SECRET_KEY` 已设置

整个 demo 建议统一使用一组 **fresh** 的数据，避免重复录制时撞上已存在邮箱或 case：

- `owner email = owner.tm3.20260418@example.com`
- `invitee email = adjuster.tm3.20260418@example.com`
- `case_id = tm3-collab-20260418`

如果你重录，请把日期或末尾数字换掉。

这个版本建议录制 3.5 到 5 分钟，重点讲“在 Milestone 2 基础上，系统如何从单用户 AI demo 继续走向更产品化的 authenticated backend”。更完整的多用户加入、聊天历史和实时房间，可以放到 Milestone 4 再讲。

### 1. 展示 `GET /health`

1. 在 `/docs` 页面找到 `GET /health`
2. 点开这一栏
3. 点 `Try it out`
4. 点 `Execute`
5. 停一下，让画面显示 response body

重点让老师看到：

- `"status": "ok"`
- `"ai_ready": true`

Script:

First, I’m checking the health endpoint.

This confirms that the backend is live and that the AI system is ready.

### 2. 展示认证流程：`POST /auth/register` + Swagger `Authorize` + `GET /auth/me`

这一段建议连续展示，这样可以少一个点，但逻辑更完整。

#### 2A. 先展示 `POST /auth/register`

1. 找到 `POST /auth/register`
2. 点开
3. 点 `Try it out`
4. 在 request body 里填下面这段：

```json
{
  "email": "owner.tm3.20260418@example.com",
  "password": "ClaimMate123",
  "display_name": "Mingtao Owner"
}
```

5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `access_token`
- `token_type`
- `user`

Script:

One major addition after Milestone 2 is authentication.

Here I’m registering a user for the first time. In the response, we can see an access token, the token type, and the public user object.

This means the system is no longer only a demo backend for anonymous calls. It now supports authenticated user identity, which is the foundation for case ownership, invite-based collaboration, and protected case access.

#### 2B. 再展示 Swagger `Authorize` + `GET /auth/me`

1. 先点击 Swagger 右上角 `Authorize`
2. 在 Bearer token 输入框里粘贴上一步返回的 `access_token`
3. 关闭弹窗
4. 找到 `GET /auth/me`
5. 点 `Try it out`
6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `id`
- `email`
- `display_name`

Script:

Now I’m using that bearer token to authenticate the session.

When I call `/auth/me`, the backend returns the current authenticated user.

This is a simple step, but it is important because it shows that later case actions are tied to a real user identity instead of an anonymous demo request.

### 3. 展示 `POST /cases`

1. 找到 `POST /cases`
2. 点开
3. 点 `Try it out`
4. 在 request body 里填下面这段：

```json
{
  "case_id": "tm3-collab-20260418"
}
```

5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `case_id`

Script:

Next, I’m creating a case while authenticated as the owner.

In Milestone 2, cases were mainly used as structured containers for policies, accident data, and AI context. In Milestone 3, a case also becomes an access-controlled collaboration object.

Because this request is authenticated, the backend can associate this new case with its owner, which is what makes the later invite and membership flow possible.

### 4. 展示 `POST /cases/{case_id}/demo/seed-accident`

1. 找到 `POST /cases/{case_id}/demo/seed-accident`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm3-collab-20260418`
5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `stage_a`
- `stage_b`
- `claim_dates`
- `report_payload`
- `chat_context`

Script:

To keep the demo focused, I’m seeding a prepared accident case into this authenticated case ID.

In the response, we can see structured Stage A and Stage B data, claim timeline dates, a generated report payload, and chat-ready context.

So this step reuses the Milestone 2 accident workflow foundation, but now it lives inside an authenticated case that can later be shared with other participants.

### 5. 展示邀请能力：`POST /cases/{case_id}/invites`

这一段只展示 owner 侧创建 invite，先把“可共享能力”讲清楚。第二个用户真正加入 case 的 end-to-end flow，可以放到 Milestone 4 再讲。

1. 找到 `POST /cases/{case_id}/invites`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm3-collab-20260418`
5. 在 request body 里填下面这段：

```json
{
  "role": "member",
  "expires_in_hours": 168
}
```

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `case_id`
- `token`
- `role`
- `expires_at`

Script:

Another major addition after Milestone 2 is the invite flow.

Here, as the owner, I’m creating a one-time invite for this case. In the response, we can see the invite token, the role, and the expiration time.

This is important because it shows how ClaimMate can move from a single-user case into a multi-party collaboration flow, while still keeping access controlled.

### 6. 展示聊天 AI：`POST /cases/{case_id}/chat/messages`

这一段先只展示 case-aware chat AI。更完整的聊天历史 timeline 和 WebSocket room，可以放到 Milestone 4 再讲。

1. 找到 `POST /cases/{case_id}/chat/messages`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm3-collab-20260418`
5. 在 request body 里填下面这段：

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

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `response.trigger`
- `response.metadata.stage`
- `response.text`
- `response.metadata.deadline_intent`
- `response.metadata.tracked_windows`

Script:

Here I’m using the simplified chat message endpoint in a multi-party scenario.

This is another important Milestone 3 addition, because chat is no longer just an isolated AI response call. It is now part of a case-aware, member-aware collaboration flow.

In the response, we can see that the trigger is `DEADLINE`, the stage is `stage_3`, and the metadata marks this as an explicit deadline explainer.

We can also see tracked deadline windows in the metadata, which means the backend is turning saved case dates into a case-specific timeline explanation inside a shared room context.

So the AI behavior from Milestone 2 is now being exercised inside a more product-like, collaborative chat workflow.

### Milestone 4 可继续讲的点

如果你后面要继续录 Milestone 4，很适合把这几个点接着讲：

- 第二个用户 `POST /auth/accept-invite` 真正加入 case
- `GET /cases/{case_id}/chat/messages` 展示 persistent chat history
- `WS /ws/cases/{case_id}` 展示 real-time room prototype

## 结尾

So, in  Milestone 3, I showed how ClaimMate evolved beyond the Milestone 2 AI workflow.

The backend now supports authenticated users, case ownership, invite creation, and case-aware chat behavior, while still keeping the earlier AI capabilities for policy understanding, accident context, deadlines, and disputes.

This makes the system feel much closer to a real product backend rather than only a collection of isolated AI demos, and it also sets up a clear path for Milestone 4 collaboration features.
