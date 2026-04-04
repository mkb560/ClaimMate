# 给 Lou 的前端调用示例

这份文档是给前端直接接接口用的。目标不是讲后端实现，而是告诉你现在怎么调用当前最适合前端 demo 的接口，不只是 upload + ask，也包括事故 case snapshot、报告预览和 chat event。

## 当前可用接口

当前最适合前端先接的接口有两组：

第一组，policy Q&A：

- `POST /cases/{case_id}/demo/seed-policy`
- `POST /cases/{case_id}/policy`
- `POST /cases/{case_id}/ask`

第二组，事故 / 报告 / chat：

- `POST /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/demo/seed-accident`
- `POST /cases/{case_id}/accident/report`
- `POST /cases/{case_id}/chat/event`

如果你只想先做最短 demo，还是可以只做 upload + ask；但如果你要继续接第二、第三主线，现在已经不需要自己猜接口了。

## 建议的前端页面流

最简单也最稳的 policy demo 路径：

1. 直接用固定 demo `case_id`，比如 `allstate-change-2025-05`
2. 前端调用 `/cases/{case_id}/demo/seed-policy`
3. 返回后显示 “policy 已经 indexed”
4. 用户输入一个问题
5. 前端调用 `/cases/{case_id}/ask`
6. 页面展示 answer、disclaimer、citations

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

## 2. 上传 policy PDF

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

## 3. 提问 ask API

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

## 3. 前端建议的数据类型

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
  created_at: string
  updated_at: string
}
```

## 4. React 页面最小示例

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

## 5. citations 怎么展示最好

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

## 6. 事故 / chat 直接可用的 demo case

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

### 触发 stage 3 chat event

```ts
export async function sendChatEvent(caseId: string) {
  const response = await fetch(`/cases/${caseId}/chat/event`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      sender_role: "owner",
      message_text: "@AI What is the 15-day acknowledgment rule for a California claim?",
      participants: [
        { user_id: "owner-1", role: "owner" },
        { user_id: "adjuster-1", role: "adjuster" },
      ],
      invite_sent: true,
      trigger: "MESSAGE",
      metadata: { demo_label: "claim_rule_stage_3" },
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || "Chat event failed")
  }

  return response.json()
}
```

## 7. 推荐 demo 问题

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

## 8. 前端需要注意的错误情况

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

## 9. 现阶段最推荐你先做的 UI

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
