# 给 Lou 的前端调用示例

这份文档是给前端直接接接口用的。目标不是讲后端实现，而是告诉你现在怎么调用这两个最小 API，把 upload + ask 的 demo 页面先做出来。

## 当前可用接口

当前后端已经接好了两个最小接口：

- `POST /cases/{case_id}/policy`
- `POST /cases/{case_id}/ask`

推荐你先只围绕这两个接口做页面。

## 建议的前端页面流

最简单也最稳的 demo 路径：

1. 用户输入或生成一个 `case_id`
2. 用户上传一份 PDF
3. 前端调用 `/cases/{case_id}/policy`
4. 上传成功后，显示 “policy 已经 indexed”
5. 用户输入一个问题
6. 前端调用 `/cases/{case_id}/ask`
7. 页面展示 answer、disclaimer、citations

## 1. 上传 policy PDF

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

## 2. 提问 ask API

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

你可以先在前端写这两个类型：

```ts
export type UploadPolicyResponse = {
  case_id: string
  filename: string
  chunk_count: number
  status: string
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

## 6. 推荐 demo 问题

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

## 7. 前端需要注意的错误情况

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

## 8. 现阶段最推荐你先做的 UI

第一版建议你先做：

1. caseId 输入框
2. PDF 上传区
3. 问题输入框
4. 回答展示区
5. citations 展示区

只要这五块先出来，整个 demo 就已经能跑。
