# 给 Lou 的前端调用示例

这份文档是给前端直接接接口用的。目标不是讲后端实现，而是告诉你现在怎么调用当前最适合前端 demo 的接口，不只是 upload + ask，也包括事故 case snapshot、报告预览和 chat event/messages timeline。

## 当前可用接口

当前最适合前端先接的接口有两组：

第一组，policy Q&A：

- `GET /demo/policies`
- `GET /cases/{case_id}/policy`
- `POST /cases/{case_id}/demo/seed-policy`
- `POST /cases/{case_id}/policy`
- `POST /cases/{case_id}/ask`

第二组，事故 / 报告 / chat：

- `POST /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/demo/seed-accident`
- `POST /cases/{case_id}/accident/report`
- `GET /cases/{case_id}/chat/messages`
- `POST /cases/{case_id}/chat/messages`
- `POST /cases/{case_id}/chat/event`

如果你只想先做最短 demo，还是可以只做 upload + ask；但如果你要继续接第二、第三主线，现在已经不需要自己猜接口了。

## 建议的前端页面流

最简单也最稳的 policy demo 路径：

1. 先 `GET /demo/policies`，拿到 demo policy 列表
2. 直接用固定 demo `case_id`，比如 `allstate-change-2025-05`
3. 前端调用 `/cases/{case_id}/demo/seed-policy`
4. 再 `GET /cases/{case_id}/policy`，确认当前已经 indexed 哪份 policy
5. 用户输入一个问题
6. 前端调用 `/cases/{case_id}/ask`
7. 页面展示 answer、disclaimer、citations

如果你要支持真实上传，再补：

1. 用户输入或生成一个 `case_id`
2. 用户上传一份 PDF
3. 前端调用 `/cases/{case_id}/policy`
4. 上传成功后，显示文件名和 chunk 数量

事故 / chat demo 的最短路径：

1. 用固定 `case_id`：`demo-accident-2026-04`
2. 先 `POST /cases/{case_id}/demo/seed-accident`
3. 再 `GET /cases/{case_id}` 读取当前 snapshot
4. 如果要刷新报告，调用 `POST /cases/{case_id}/accident/report`
5. 再次 `GET /cases/{case_id}`，拿新的 `report_payload` / `chat_context`
6. 用 `POST /cases/{case_id}/chat/event` 展示 AI chat response
7. 如果页面要展示时间线，用 `POST /cases/{case_id}/chat/messages` 写入消息，再用 `GET /cases/{case_id}/chat/messages` 读取 timeline

## 1. Seed 固定 demo policy

### 请求

接口：

```text
POST /cases/{case_id}/demo/seed-policy
```

如果 `case_id` 本身就是固定 demo case，可以直接空 body 调用：

- `allstate-change-2025-05`
- `allstate-renewal-2025-08`
- `progressive-verification-2026-03`

如果你想把固定 demo PDF 种到自定义 `case_id`，请求体传：

```json
{
  "policy_key": "progressive-verification"
}
```

### 前端调用示例

```ts
export async function seedDemoPolicy(caseId: string, policyKey?: string) {
  const response = await fetch(`/cases/${caseId}/demo/seed-policy`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(policyKey ? { policy_key: policyKey } : {}),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Seed demo policy failed")
  }

  return response.json()
}
```

### 成功返回示例

```json
{
  "case_id": "allstate-change-2025-05",
  "policy_key": "allstate-change",
  "default_case_id": "allstate-change-2025-05",
  "label": "Allstate policy change packet",
  "filename": "TEMP_PDF_FILE.pdf",
  "chunk_count": 6,
  "status": "indexed",
  "sample_questions": [
    "Who are the policyholders and what is the policy number?",
    "What policy change is confirmed and when is it effective?"
  ]
}
```

### 前端拿到后建议做什么

- 显示已加载哪一份 demo policy
- 把 `sample_questions` 做成快捷按钮
- 直接解锁 ask 输入框，不再要求手动上传

## 2. 读取 demo policy catalog

### 请求

接口：

```text
GET /demo/policies
```

### 成功返回示例

```json
{
  "policies": [
    {
      "policy_key": "allstate-change",
      "default_case_id": "allstate-change-2025-05",
      "label": "Allstate policy change packet",
      "filename": "TEMP_PDF_FILE.pdf",
      "sample_questions": [
        "Who are the policyholders and what is the policy number?"
      ]
    }
  ]
}
```

### 前端最适合怎么用

- 做一个 demo policy picker
- 用 `default_case_id` 直接填 case selector
- 用 `sample_questions` 做快捷问题

## 3. 读取当前 case 的 policy 状态

### 请求

接口：

```text
GET /cases/{case_id}/policy
```

### 成功返回示例

```json
{
  "case_id": "allstate-change-2025-05",
  "has_policy": true,
  "chunk_count": 10,
  "source_label": "Your Policy (TEMP_PDF_FILE.pdf)",
  "filename": "TEMP_PDF_FILE.pdf",
  "demo_policy": {
    "policy_key": "allstate-change",
    "default_case_id": "allstate-change-2025-05",
    "label": "Allstate policy change packet",
    "filename": "TEMP_PDF_FILE.pdf",
    "sample_questions": [
      "Who are the policyholders and what is the policy number?"
    ]
  }
}
```

### 前端最适合怎么用

- 页面刷新后恢复 “当前已经索引了哪份 policy”
- 决定 ask 输入框是否应该可用
- 如果 `demo_policy` 不为空，直接显示推荐问题

## 4. 上传 policy PDF

### 请求

接口：

```text
POST /cases/{case_id}/policy
```

请求类型：

```text
multipart/form-data
```

字段名必须叫：

```text
file
```

### 前端调用示例

```ts
export async function uploadPolicy(caseId: string, file: File) {
  const formData = new FormData()
  formData.append("file", file)

  const response = await fetch(`/cases/${caseId}/policy`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Upload failed")
  }

  return response.json()
}
```

### 成功返回示例

```json
{
  "case_id": "demo-case",
  "filename": "Verification-of-Insurance.pdf",
  "chunk_count": 1,
  "status": "indexed"
}
```

### 前端拿到后建议做什么

- 显示上传成功提示
- 显示文件名
- 显示 chunk 数量
- 自动解锁问答输入框

## 5. 提问 ask API

### 请求

接口：

```text
POST /cases/{case_id}/ask
```

请求体：

```json
{
  "question": "What is the policy number, policy period, and insurer?"
}
```

### 前端调用示例

```ts
export async function askPolicyQuestion(caseId: string, question: string) {
  const response = await fetch(`/cases/${caseId}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Ask request failed")
  }

  return response.json()
}
```

### 成功返回示例

```json
{
  "case_id": "api-smoke",
  "question": "What is the policy number, policy period, and insurer?",
  "answer": "The policyholders listed in the document are Mingtao Ding, Yizhan Huang. [S1] The policy number is 871890019. [S1] The policy period is Apr 4, 2026 to Oct 4, 2026, and the insurer listed in the document is Progressive Select Ins Co. [S1][S1]\n\nDisclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
  "disclaimer": "Disclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
  "citations": [
    {
      "source_type": "kb_a",
      "source_label": "Your Policy (Verification-of-Insurance.pdf)",
      "document_id": "policy_pdf",
      "page_num": 1,
      "section": "PROGRESSIVE",
      "excerpt": "Policyholders: Mingtao Ding Yizhan Huang Page 1 of 1"
    }
  ]
}
```

## 6. 前端建议的数据类型

至少建议先写这些类型：

```ts
export type UploadPolicyResponse = {
  case_id: string
  filename: string
  chunk_count: number
  status: string
}

export type SeedDemoPolicyResponse = {
  case_id: string
  policy_key: string
  default_case_id: string
  label: string
  filename: string
  chunk_count: number
  status: string
  sample_questions: string[]
}

export type Citation = {
  source_type: "kb_a" | "kb_b"
  source_label: string
  document_id: string
  page_num: number | null
  section: string | null
  excerpt: string
}

export type AskResponse = {
  case_id: string
  question: string
  answer: string
  disclaimer: string
  citations: Citation[]
}

export type CaseSnapshotResponse = {
  case_id: string
  claim_notice_at: string | null
  proof_of_claim_at: string | null
  last_deadline_alert_at: string | null
  stage_a: Record<string, unknown>
  stage_b: Record<string, unknown> | null
  report_payload: Record<string, unknown> | null
  chat_context: Record<string, unknown> | null
  room_bootstrap: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type ChatMessage = {
  id: string
  case_id: string
  sender_role: string
  message_text: string
  created_at: string
  ai_response?: Record<string, unknown> | null
}
```

## 7. React 页面最小示例

下面这个例子不是完整 UI，只是最小 happy path。

```tsx
import { useState } from "react"

export default function DemoAskPage() {
  const [caseId, setCaseId] = useState("demo-case")
  const [file, setFile] = useState<File | null>(null)
  const [question, setQuestion] = useState("")
  const [uploadResult, setUploadResult] = useState<any>(null)
  const [askResult, setAskResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    setError("")
    try {
      const result = await uploadPolicy(caseId, file)
      setUploadResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setLoading(false)
    }
  }

  async function handleAsk() {
    if (!question.trim()) return
    setLoading(true)
    setError("")
    try {
      const result = await askPolicyQuestion(caseId, question)
      setAskResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <input value={caseId} onChange={(e) => setCaseId(e.target.value)} />
      <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <button onClick={handleUpload} disabled={loading || !file}>Upload</button>

      <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
      <button onClick={handleAsk} disabled={loading || !question.trim()}>Ask</button>

      {error ? <p>{error}</p> : null}
      {uploadResult ? <pre>{JSON.stringify(uploadResult, null, 2)}</pre> : null}
      {askResult ? <pre>{JSON.stringify(askResult, null, 2)}</pre> : null}
    </div>
  )
}
```

## 8. citations 怎么展示最好

前端不要直接把整个 `citations` JSON 粘出来，建议做成比较清楚的卡片或列表。

推荐展示顺序：

1. `source_label`
2. 来源标签
3. 页码
4. section
5. excerpt

### 来源标签建议

你可以把：

- `kb_a` 显示成 `Your Policy`
- `kb_b` 显示成 `Regulation`

### 渲染示例

```tsx
function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div>
      {citations.map((citation, index) => (
        <div key={`${citation.document_id}-${index}`}>
          <strong>{citation.source_label}</strong>
          <div>
            {citation.source_type === "kb_a" ? "Your Policy" : "Regulation"}
            {citation.page_num ? ` | Page ${citation.page_num}` : ""}
            {citation.section ? ` | ${citation.section}` : ""}
          </div>
          <p>{citation.excerpt}</p>
        </div>
      ))}
    </div>
  )
}
```

## 9. Stage A / Stage B 表单提交

### PATCH Stage A

接口：

```text
PATCH /cases/{case_id}/accident/stage-a
```

请求体是 deep-merge 的，所以你只需要传这次改了的字段，不需要传完整对象。字段名对着 `backend/models/accident_types.py` 里的 snake_case 来。

请求体示例：

```json
{
  "occurred_at": "2026-04-01T14:30:00Z",
  "location": { "address": "123 Main St, Los Angeles, CA" },
  "owner_party": { "role": "owner", "name": "Jane Doe", "phone": "555-1234", "insurer": "Allstate", "policy_number": "123456789" },
  "other_party": { "role": "other_driver", "name": "John Smith", "phone": "555-5678" },
  "injuries_reported": false,
  "police_called": true,
  "drivable": true,
  "tow_requested": false,
  "quick_summary": "Rear-end collision at a red light.",
  "stage_completed_at": "2026-04-01T15:00:00Z"
}
```

成功返回示例：

```json
{
  "case_id": "demo-case",
  "stage_a": { "...merged stage A JSON..." }
}
```

### PATCH Stage B

接口：

```text
PATCH /cases/{case_id}/accident/stage-b
```

请求体示例：

```json
{
  "detailed_narrative": "Stopped at a red light and was hit from behind.",
  "damage_summary": "Rear bumper cracked, trunk misalignment.",
  "weather_conditions": "Clear",
  "road_conditions": "Dry",
  "police_report_number": "LA-2026-04-0001",
  "adjuster_name": "Mike Adams",
  "repair_shop_name": "AutoFix LA",
  "follow_up_notes": "Waiting for adjuster estimate.",
  "stage_completed_at": "2026-04-02T10:00:00Z"
}
```

成功返回示例：

```json
{
  "case_id": "demo-case",
  "stage_b": { "...merged stage B JSON..." }
}
```

## 9.5. 创建 case / 删除 case / claim dates / 读取报告

### 创建 case

```text
POST /cases
```

请求体（可选）：

```json
{ "case_id": "my-custom-id" }
```

空 body 也行，服务器会自动生成 `case-...` ID。

成功返回：

```json
{ "case_id": "my-custom-id" }
```

### 删除 case（demo 清理用）

```text
DELETE /cases/{case_id}
```

成功返回 `204 No Content`，会同时删除关联的 vector chunks 和 chat messages。

### 更新 claim dates

```text
PATCH /cases/{case_id}/claim-dates
```

请求体：

```json
{
  "claim_notice_at": "2026-04-01T10:00:00Z",
  "proof_of_claim_at": "2026-04-03T10:00:00Z"
}
```

这两个日期用于 AI 的 deadline 计算（15-day acknowledgment / 40-day decision window）。

### 读取已生成的事故报告

```text
GET /cases/{case_id}/accident/report
```

和 `POST` 不同，`GET` 只读取之前 `POST` 生成并缓存过的报告。如果还没生成过，返回 `404`。

成功返回：

```json
{
  "case_id": "demo-case",
  "report_payload": { "...same as POST response..." },
  "chat_context": { "...same as POST response..." }
}
```

## 10. 事故 / chat 直接可用的 demo case

现在仓库里已经固定了一条事故 demo case：

- `demo-accident-2026-04`

如果你本地或共享后端已经跑过：

- [seed_accident_demo.py](/Users/dingmingtao/Desktop/USC/研二下/DSCI560/ClaimMate/backend/scripts/seed_accident_demo.py)

你就可以直接这样用：

### 读取 snapshot

```ts
export async function getCaseSnapshot(caseId: string) {
  const response = await fetch(`/cases/${caseId}`, {
    method: "GET",
    cache: "no-store",
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Load case snapshot failed")
  }

  return response.json()
}
```

### 一键 seed 固定事故 demo case

```ts
export async function seedAccidentDemoCase(caseId: string) {
  const response = await fetch(`/cases/${caseId}/demo/seed-accident`, {
    method: "POST",
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Seed accident demo failed")
  }

  return response.json()
}
```

### 触发 report 重新生成

```ts
export async function generateAccidentReport(caseId: string) {
  const response = await fetch(`/cases/${caseId}/accident/report`, {
    method: "POST",
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Generate report failed")
  }

  return response.json()
}
```

### 触发 chat event

`sendChatEvent` 需要传入完整的 `ChatEventRequest` payload，不要硬编码在函数里：

```ts
export type ChatEventRequest = {
  sender_role: string
  message_text: string
  participants: Array<{ user_id: string; role: string }>
  invite_sent: boolean
  trigger: "MESSAGE" | "PARTICIPANT_JOINED" | "POLICY_INDEXED"
  metadata?: Record<string, unknown>
}

export async function sendChatEvent(caseId: string, payload: ChatEventRequest) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/chat/event`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Chat event failed")
  }

  return response.json()
}
```

调用示例（stage 3 demo）：

```ts
const result = await sendChatEvent("demo-accident-2026-04", {
  sender_role: "owner",
  message_text: "@AI What is the 15-day acknowledgment rule for a California claim?",
  participants: [
    { user_id: "owner-1", role: "owner" },
    { user_id: "adjuster-1", role: "adjuster" },
  ],
  invite_sent: true,
  trigger: "MESSAGE",
  metadata: { demo_label: "claim_rule_stage_3" },
})
```

### 写入并读取 chat timeline

如果前端要展示完整时间线，优先用简化版 messages API：

```ts
export async function sendChatMessage(caseId: string, messageText: string) {
  const response = await fetch(`/cases/${caseId}/chat/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      sender_role: "owner",
      message_text: messageText,
      participants: [
        { user_id: "owner-1", role: "owner" },
        { user_id: "adjuster-1", role: "adjuster" },
      ],
      invite_sent: true,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Send chat message failed")
  }

  return response.json()
}

export async function getChatMessages(caseId: string) {
  const response = await fetch(`/cases/${caseId}/chat/messages`, {
    method: "GET",
    cache: "no-store",
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Load chat messages failed")
  }

  return response.json()
}
```

## 11. 推荐 demo 问题

如果你要先做固定 demo，可以直接用这些问题：

### 对 `allstate-change-2025-05`

- `Who are the policyholders and what is the policy number?`
- `What policy change is confirmed and when is it effective?`

### 对 `allstate-renewal-2025-08`

- `What optional coverage is highlighted in this renewal offer?`
- `What should the insurer do within 15 days after receiving notice of claim?`

### 对 `progressive-verification-2026-03`

- `What is the policy number, policy period, and insurer?`
- `Does this document say it is a full insurance policy or only verification of insurance?`

## 12. 前端需要注意的错误情况

### 上传阶段

- 不是 PDF
- 文件为空
- 后端没配置好 `OPENAI_API_KEY`
- 后端没配置好 `DATABASE_URL`

### 提问阶段

- `question` 为空
- `case_id` 非法
- 还没先上传 policy

建议前端统一 toast 或 inline error 文案，不要只在 console 里报错。

## 13. 现阶段最推荐你先做的 UI

第一版建议你先做：

1. caseId 输入框
2. PDF 上传区
3. 问题输入框
4. 回答展示区
5. citations 展示区
6. accident case snapshot 预览区
7. report summary / comparison rows 预览区
8. chat event response 展示区

只要这几块先出来，第一、第二、第三主线都能在一个 demo 页里被看见。
