# 给 Ke 的最小接口契约

这份文档不是最终生产 API 规范，而是当前 demo 阶段最小可用接口契约。目标只有一个：让前端能上传保单、提问、拿到 grounded answer + citations。

## 当前建议优先实现的 2 个接口

### 1. 上传保单

`POST /cases/{case_id}/policy`

用途：
- 上传一份 policy PDF
- 写入 KB-A
- 返回 ingest 结果

建议请求方式：
- `multipart/form-data`
- 文件字段名：`file`

建议返回：

```json
{
  "case_id": "allstate-change-2025-05",
  "filename": "TEMP_PDF_FILE.pdf",
  "chunk_count": 10,
  "status": "indexed"
}
```

### 2. 提问

`POST /cases/{case_id}/ask`

建议请求体：

```json
{
  "question": "Who are the policyholders and what is the policy number?"
}
```

建议返回体：

```json
{
  "answer": "The policyholders listed in the document are Anlan Cai, Mingtao Ding. [S1] The policy number is 804 448 188. [S1]\n\nDisclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
  "disclaimer": "This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
  "citations": [
    {
      "source_type": "kb_a",
      "source_label": "Your Policy (TEMP_PDF_FILE.pdf)",
      "document_id": "policy_pdf",
      "page_num": 1,
      "section": null,
      "excerpt": "Policyholder(s) Anlan Cai Mingtao Ding Policy number 804 448 188"
    }
  ]
}
```

## Citation 字段约定

`citations[]` 里当前建议前后端统一使用这些字段：

- `source_type`
  - `kb_a` 表示用户 policy
  - `kb_b` 表示 regulatory/reference source
- `source_label`
  - 给前端直接展示的人类可读标题
- `document_id`
  - 程序内来源 ID
- `page_num`
  - 文档页码
- `section`
  - 只有可读时才返回；如果是 OCR 噪音会直接给 `null`
- `excerpt`
  - 截断后的引用片段

## 为什么要保留 `source_type`

前端很需要知道 citation 是：

- 来自用户自己的保单
- 还是来自 California / NAIC 这类外部法规资料

所以不要只给前端一个字符串标题；最好明确给 `source_type`。

## 当前后端建议直接调用的函数

### 保单 ingest

优先调用：

- `ai.ingestion.ingest_policy.ingest_local_policy_file(...)`

如果后面你改成真正的对象存储上传，再接：

- `ingest_policy(...)`

### 提问

优先调用：

- `ai.rag.query_engine.answer_policy_question(case_id, question)`

## 当前不建议第一阶段就做太重的接口

先不要把第一版搞成很大的统一 AI gateway。

不建议第一阶段优先做：

- 太复杂的 websocket 设计
- 一次性把 chat / deadline / dispute 全接完
- 很大的 REST schema 体系

当前最优先的是先把 upload + ask 路走通。

## 第二阶段可补的接口

当第一阶段稳定后，再考虑：

### Claim dates 更新

`PATCH /cases/{case_id}/claim-dates`

建议请求体：

```json
{
  "claim_notice_at": "2026-03-28T10:00:00Z",
  "proof_of_claim_at": "2026-03-30T10:00:00Z"
}
```

### Chat AI

后续可以再包：

- `handle_chat_event(...)`

但这不是第一批必须完成的东西。

## 当前接口边界建议

为了避免和 AI core 互相踩，建议边界保持这样：

- Mingtao 管 AI 内部实现、prompt、RAG、dispute、deadline 逻辑
- 你管 route、request/response schema、case storage、FastAPI wiring

如果要改这些高协调点，请先同步：

- `backend/main.py`
- `backend/models/ai_types.py`
- `backend/.env.example`
- `cases.id` 的类型
- citation 返回结构

## 当前你做完后，Lou 应该能直接拿到什么

理想状态下，Lou 只需要知道：

1. 怎么上传一份 policy PDF
2. 怎么提交一个问题
3. 返回 JSON 长什么样

只要这 3 件事稳定，前端 demo 就能快速接起来。
