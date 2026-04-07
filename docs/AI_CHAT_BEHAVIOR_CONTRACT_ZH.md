# AI Chat 行为契约

这份文档只描述 Mingtao 负责的 AI chat 行为边界，方便 Ke 和 Lou 在 app-layer / frontend 接入时知道什么时候会有 AI 回复，以及应该展示哪些字段。

## 触发规则

- `POLICY_INDEXED`：只有在 `stage_1` 会主动生成 policy indexed 后的 AI 摘要。
- `@AI` mention：用户消息包含 `@AI` 时，AI 会把 mention 后面的内容当作问题处理。
- 空 `@AI`：如果用户只发 `@AI`，AI 会回复 `Please add a question after @AI...`，不会继续查 policy 或 deadline。
- dispute signal：如果消息里出现 `denied my claim`、`claim denied`、`bad faith`、`underpaid`、`refuse to pay` 等 dispute 触发词，AI 会走 dispute path。
- deadline fallback：只有在普通消息没有 `@AI`、没有 dispute signal 时，AI 才会检查 deadline reminder。

## 优先级

当前 `handle_chat_event(...)` 的优先级是：

1. `POLICY_INDEXED` + `stage_1` 主动摘要
2. `@AI` mention
3. mention 内部如果命中 dispute signal，则切到 dispute path
4. 非 mention 消息如果命中 dispute signal，则切到 dispute path
5. deadline reminder fallback

这意味着：如果一条消息已经被 `@AI` 或 dispute 处理，deadline reminder 不应该抢先触发。

## Stage 语气

- `stage_1`：只有 owner，语气可以更直接、教育性更强。
- `stage_2`：owner 已经准备邀请 adjuster 或 repair shop，但外部人员还没加入，AI 会更关注材料准备和时间线。
- `stage_3`：adjuster 或 repair shop 已经在房间里，AI 必须保持中立。所有 stage 3 answer 都应该以 `For reference:` 开头。

## Response 字段

前端展示 AI 回复时重点使用：

- `text`：AI 回复正文。
- `citations`：引用来源。policy/RAG/dispute 回答通常应该展示 citation；deadline reminder 可能没有 citation。
- `trigger`：`MENTION`、`DISPUTE`、`PROACTIVE` 或 `DEADLINE`。
- `metadata.stage`：`stage_1`、`stage_2` 或 `stage_3`。
- `metadata.dispute_type`：dispute path 才有，例如 `DENIAL`。
- `metadata.recommended_statute`：dispute path 才有，用于说明建议参考的法规方向。
- `metadata.deadline_type`：deadline reminder 才有，例如 `acknowledgment`。

## 回归检查

Mingtao 线的 chat AI 行为可以用下面的 deterministic eval 检查，不需要真实 OpenAI 或数据库：

```bash
cd backend
./.venv/bin/python scripts/run_chat_ai_eval.py --json-out /tmp/claimmate_chat_ai_eval.json
```

这条 eval 覆盖：

- 空 `@AI`
- stage 1 policy / regulatory mention
- stage 3 neutral `For reference:` 前缀
- 非 mention dispute trigger
- deadline fallback
- policy indexed proactive response
