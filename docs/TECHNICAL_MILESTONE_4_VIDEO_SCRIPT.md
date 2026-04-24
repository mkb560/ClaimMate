# Technical Milestone 4 Video Script

## 开场

Hi, I’m Mingtao Ding, and this is Technical Milestone 4 for me.

In Milestone 3, I showed how ClaimMate moved beyond an anonymous AI demo and became an authenticated backend with case ownership, invite creation, and case-aware chat AI.

In Milestone 4, I continue from that foundation and focus on the next layer: a second participant actually joining the case, persistent chat history inside the shared case, and a lightweight real-time room prototype.

## 操作 + Script

这次建议把 Milestone 4 录成一个 **承接 Milestone 3 的 continuation demo**，不需要重新把 health、register owner、create case、seed accident、create invite 全讲一遍。

建议默认你已经完成了 Milestone 3 的前半段，并且手里已经有：

- `owner token`
- `invite token`
- `case_id = tm4-collab-20260419`

如果你想单独录 Milestone 4，也可以先快速做完 Milestone 3 的前 5 步，再从这里接着录。

整个版本建议录制 3 到 4 分钟，重点讲：

- 第二个用户真正加入 case
- case 里的聊天历史会被持久化
- 同一个 case 可以有实时房间原型

### 1. 展示第二个用户的 `POST /auth/register` + `POST /auth/accept-invite`

这一段建议你口头说明“现在切到第二个用户视角”，然后把 Swagger 的 Bearer token 改成第二个用户的新 token。

#### 1A. 先展示第二个用户的 `POST /auth/register`

1. 找到 `POST /auth/register`
2. 点开
3. 点 `Try it out`
4. 在 request body 里填下面这段：

```json
{
  "email": "adjuster.tm4.20260419@example.com",
  "password": "ClaimMate123",
  "display_name": "Adjuster Demo"
}
```

5. 点 `Execute`
6. 复制返回的 `access_token`

#### 1B. 再展示 Swagger `Authorize` + `POST /auth/accept-invite`

1. 点击 Swagger 右上角 `Authorize`
2. 把 Bearer token 替换成第二个用户的 token
3. 找到 `POST /auth/accept-invite`
4. 点 `Try it out`
5. 在 request body 里填下面这段：

```json
{
  "token": "PASTE_THE_INVITE_TOKEN_HERE"
}
```

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `case_id`
- `accepted`

Script:

In Milestone 3, I showed that the owner can create an invite.  
Here in Milestone 4, I’m switching to a second authenticated user and using that invite to actually join the same case.

In the response, we can see that the invite is accepted for the same case ID.

This is important because the system is no longer only generating invite tokens. It now supports real membership changes, which is a key step toward a true multi-party claims workflow.

### 2. 展示 `GET /cases/{case_id}` 或 `GET /auth/me`

这一段建议只选一个最顺手的：

- 如果你想强调“现在是第二个用户身份”，就用 `GET /auth/me`
- 如果你想强调“第二个用户已经能访问同一个 case”，就用 `GET /cases/{case_id}`

更推荐你用 `GET /cases/{case_id}`，因为它更能体现 collaboration。

1. 找到 `GET /cases/{case_id}`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm4-collab-20260419`
5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `case_id`
- `report_payload`
- `chat_context`
- `room_bootstrap`

Script:

Now I’m loading the same case as the second user.

This shows that the invited participant can access the shared case context, including the generated report payload, the chat-ready context, and the room bootstrap data.

So the case is no longer tied to only one user. It is becoming a shared collaboration object.

### 3. 展示 `POST /cases/{case_id}/chat/messages` + `GET /cases/{case_id}/chat/messages`

这一段建议连续展示，先发一条消息，再读出历史。

#### 3A. 先展示 `POST /cases/{case_id}/chat/messages`

1. 找到 `POST /cases/{case_id}/chat/messages`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm4-collab-20260419`
5. 在 request body 里填下面这段：

```json
{
  "message_text": "@AI what deadlines should I know for this claim?",
  "sender_role": "adjuster",
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

#### 3B. 再展示 `GET /cases/{case_id}/chat/messages`

1. 找到 `GET /cases/{case_id}/chat/messages`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm4-collab-20260419`
5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `messages`
- 用户消息和 AI 消息都在 timeline 里

Script:

Here I’m sending a chat message inside the shared case, and then loading the stored chat timeline.

This is one of the clearest Milestone 4 additions. The system is no longer only returning one-off AI responses. It now keeps an append-only case timeline that both people can build on.

That makes the backend feel much closer to a real collaborative claims product.

### 4. 可选加分片段：展示 `WS /ws/cases/{case_id}`

这一段建议只录 20 到 30 秒，不需要太长。

建议展示方式：

1. 打开一个终端，说明你现在演示的是实时房间原型
2. 用两个 websocket client 连接：
   - `ws://127.0.0.1:8000/ws/cases/tm4-collab-20260419?token=...`
3. 展示：
   - `ready`
   - `pong`
4. 发一个 chat JSON
5. 展示另一个 client 也能收到：
   - `user_message`
   - `ai_message`

重点让老师看到：

- `ready`
- `pong`
- `user_message`
- `ai_message`

Script:

As an optional final step, I can also show the WebSocket room prototype.

This is still a lightweight in-memory room rather than a production-scaled real-time system, but it demonstrates that the same shared case can now support live collaborative messaging on top of the same AI dispatch logic.

So by Milestone 4, ClaimMate is moving beyond authenticated case ownership into real collaborative room behavior.

## 结尾

So, in Technical Milestone 4, I showed the next step beyond Milestone 3.

The backend now supports a second participant actually joining the case, persistent shared chat history, and a real-time room prototype for live case communication.

Together with the earlier AI features for policy understanding, accident context, deadlines, and disputes, this makes ClaimMate feel much closer to a collaborative claims product instead of only an AI demo backend.
