# Technical Milestone 2 Video Script

## 开场

Hi, I’m Mingtao Ding, and this is Technical Milestone 2 for ClaimMate.

In Milestone 1, I demonstrated policy ingestion and grounded question answering.

In Milestone 2, I build on that foundation and show what was added after Milestone 1: expanded deterministic policy fact extraction, accident report and chat-ready context generation, and stage-aware AI support for claim deadlines and disputes.

## 操作 + Script

推荐继续直接用 FastAPI Swagger 页面录制。

先打开：

- 本地后端：`http://127.0.0.1:8000/docs`
- 如果你想用 shared backend，就把地址换成对应的 `.../docs`

整个 demo 统一使用：

- `case_id = tm2-e2e-demo`
- `policy_key = allstate-change`

这个版本建议录制 4 到 6 分钟，重点讲“在 Milestone 1 基础上新增了什么”。

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

This confirms that the backend is live and that the AI system is ready. Just like in Milestone 1, this gives us a clean starting point for the demo.

### 2. 展示 `POST /cases/{case_id}/demo/seed-policy`

1. 找到 `POST /cases/{case_id}/demo/seed-policy`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm2-e2e-demo`
5. 在 request body 里填下面这段：

```json
{
  "policy_key": "allstate-change"
}
```

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `case_id`
- `policy_key`
- `filename`
- `chunk_count`
- `status`

Script:

Next, I’m seeding a demo insurance policy into a fresh case.

This part is still the foundation from Milestone 1: the system loads a sample policy PDF, processes it, and indexes it so the case is ready for grounded question answering.

I’m using the same case for the rest of the demo so we can move from policy understanding into accident workflow and AI-assisted claim support.

### 3. 展示 `POST /cases/{case_id}/ask`

1. 找到 `POST /cases/{case_id}/ask`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm2-e2e-demo`
5. 在 request body 里填下面这段：

```json
{
  "question": "What are the liability limits, and is rental reimbursement purchased?"
}
```

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `question`
- `answer`
- `citations`

Script:

Here I’m asking a more structured policy question than I showed in Milestone 1.

In the response, we can see that the system does not just return a generic summary. It gives a specific grounded answer: rental reimbursement is listed as not purchased, and the liability limits are fifty thousand dollars per person, one hundred thousand dollars per occurrence, and fifty thousand dollars for property damage.

We can also see the citation pointing back to the policy source.

So instead of only answering basic metadata, the system can now deterministically extract more practical coverage facts. This makes the answer more stable for common insurance questions and reduces reliance on free-form generation.

### 4. 展示 `POST /cases/{case_id}/demo/seed-accident`

1. 找到 `POST /cases/{case_id}/demo/seed-accident`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm2-e2e-demo`
5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `stage_a`
- `stage_b`
- `claim_dates`
- `report_payload`
- `chat_context`

Script:

This is one of the major additions in Technical Milestone 2.

Now the system can seed a structured accident case, including Stage A and Stage B accident data, saved claim dates, a generated report payload, and chat-ready context.

In the response, we can directly see the different layers of the workflow. `stage_a` captures the on-scene facts, `stage_b` captures the follow-up details, `claim_dates` stores the key timeline dates, `report_payload` gives us a structured accident report, and `chat_context` prepares the case for later AI-assisted communication.

We can also see that the backend is not just storing raw form input. It is organizing the case into reusable structured outputs, including an accident summary, key facts, and party comparison rows.

So compared with Milestone 1, the project is no longer only about policy question answering. It now starts to support the broader claim workflow after an accident.

### 5. 展示 `GET /cases/{case_id}`

1. 找到 `GET /cases/{case_id}`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm2-e2e-demo`
5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `stage_a`
- `stage_b`
- `report_payload`
- `chat_context`
- `room_bootstrap`

Script:

Here I’m loading the full case snapshot.

This shows that the backend now stores more than just policy data. It also stores structured accident intake, generated report content, chat context, and room bootstrap data that can later support product workflows like report preview and multi-party chat.

This is an important step toward an end-to-end claims assistant rather than a single-feature demo.

### 6. 展示第一个 `POST /cases/{case_id}/chat/event`

这一段用来展示显式 Deadline Explainer。

1. 找到 `POST /cases/{case_id}/chat/event`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm2-e2e-demo`
5. 在 request body 里填下面这段：

```json
{
  "sender_role": "owner",
  "message_text": "@AI what deadlines should I know for this claim?",
  "participants": [
    {
      "user_id": "owner-1",
      "role": "owner"
    }
  ],
  "invite_sent": false,
  "trigger": "MESSAGE",
  "metadata": {}
}
```

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `response.trigger`
- `response.text`
- `response.metadata.deadline_intent`
- `response.metadata.tracked_windows`

Script:

Another feature added after Milestone 1 is explicit deadline explanation.

In the response, we can see that the trigger is `DEADLINE`, and the metadata tells us this is an explicit deadline explainer, not just a fallback reminder.

We can also see tracked deadline windows in the response metadata, which means the system is reading the saved claim dates in the case and turning them into case-specific timeline support.

So when the user asks about deadlines, the AI now explains the relevant claim timeline instead of giving a generic answer.

So this is no longer just question answering over documents. It is now case-aware AI behavior.

### 7. 展示第二个 `POST /cases/{case_id}/chat/event`

这一段用来展示 stage 3 多方场景下的保守 AI fallback。

1. 还是同一个接口
2. 保持 `case_id = tm2-e2e-demo`
3. 把 request body 改成：

```json
{
  "sender_role": "owner",
  "message_text": "The insurer denied my claim and I need help understanding the denial.",
  "participants": [
    {
      "user_id": "owner-1",
      "role": "owner"
    },
    {
      "user_id": "adjuster-1",
      "role": "adjuster"
    }
  ],
  "invite_sent": true,
  "trigger": "MESSAGE",
  "metadata": {}
}
```

4. 点 `Execute`
5. 停一下，让画面显示 response body

重点让老师看到：

- `response.trigger = MENTION`
- `response.text` 以 `For reference:` 开头
- `response.text` 里有 `I don't have enough information...`
- `response.citations`

Script:

Finally, this shows how the AI behaves conservatively in a stage 3 multi-party setting.

In the response, we can see that the text starts with “For reference,” which is important because this is a stage 3 multi-party setting.

We can also see that the system returns a conservative fallback: it says it does not have enough information in the uploaded policy and regulatory materials to answer confidently.

Even in this case, the response still includes citations and keeps a neutral tone. So the system is trying to stay grounded instead of overclaiming in a sensitive claim situation.

The trigger here is shown as `MENTION` in the current implementation, because when the dispute classifier does not confidently confirm the dispute path, the system falls back to the normal question-answer flow instead of forcing a stronger dispute response.

So compared with Milestone 1, the system now supports not only policy understanding, but also more careful stage-aware behavior in claim follow-up scenarios.

### 8. 录制顺序

正式录的时候，按这个顺序来：

1. `GET /health`
2. `POST /cases/tm2-e2e-demo/demo/seed-policy`
3. `POST /cases/tm2-e2e-demo/ask`
   Question: `What are the liability limits, and is rental reimbursement purchased?`
4. `POST /cases/tm2-e2e-demo/demo/seed-accident`
5. `GET /cases/tm2-e2e-demo`
6. `POST /cases/tm2-e2e-demo/chat/event`
   Question: `@AI what deadlines should I know for this claim?`
7. `POST /cases/tm2-e2e-demo/chat/event`
   Message: `The insurer denied my claim and I need help understanding the denial.`

## 结尾

So, in Technical Milestone 2, I built on the policy ingestion and grounded QA foundation from Milestone 1.

On top of that, I added expanded deterministic policy fact extraction, structured accident report and context generation, and stage-aware AI support for deadlines and disputes.

Together, these features move ClaimMate closer to an end-to-end, consumer-side car insurance claims assistant.
