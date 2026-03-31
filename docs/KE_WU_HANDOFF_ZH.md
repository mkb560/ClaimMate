# 给 Ke 的开发说明

这份说明是给你当前阶段直接开工用的，不是长期架构文档。请先按这里的任务把 AI scaffold 接进可用的产品层。

## 你现在接手的项目状态

当前仓库里，AI 核心已经有了，但产品层还很薄。

- `backend/main.py` 现在已经有：
  - `GET /health`
  - `POST /cases/{case_id}/policy`
  - `POST /cases/{case_id}/ask`
- RAG、本地 policy ingest、KB-B indexing、dispute detection、deadline checker、chat AI scaffold 都已经在 `backend/ai/` 里
- 本地已经能用真实 PDF 跑问答，也能做 citations
- 第二主线的数据契约也已经先定下来了：
  - `backend/models/accident_types.py`
  - `backend/ai/accident/report_payload_builder.py`
  - `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md`
- 现在默认模型是：
  - `RAG_MODEL=gpt-5.4-mini`
  - `RAG_REASONING_EFFORT=xhigh`
  - `CLASSIFICATION_MODEL=gpt-5.4-mini`
  - `CLASSIFICATION_REASONING_EFFORT=xhigh`
  - `EMBEDDING_MODEL=text-embedding-3-large`
- 为了兼容当前 `pgvector(1536)` 表结构，embedding 目前固定按 1536 维写入

你可以把它理解成：
AI 核心已经能单独跑，但还没有被包装成前端可直接调用的 API。

## 你负责什么

你当前最重要的职责不是改 prompt，而是把现有 AI 能力接进应用层。

优先负责这些事情：

1. 把数据库 engine 和 vector store bootstrap 接进 FastAPI 启动流程
2. 定义最小可用的 `cases` 数据结构和相关字段
3. 做最小 API，让前端能上传 policy、提问、拿回答
4. 把第二主线的事故表单数据、报告生成入口和后续 chat 衔接接进应用层
5. 如果来得及，再补 claim dates 更新和 chat 入口

## 你第一阶段最该做的 5 件事

### 1. 先沿用现在已经有的 demo API

现在 upload / ask 这条 demo 路已经有最小可用版本，你不需要从零重新造一遍。

你优先要做的是：

- 决定这些路由后面是继续保留在 `main.py`，还是抽到 app-layer router
- 确认 case 层和未来前端对接时，request / response 不会再频繁变
- 在不破坏当前 demo 的前提下，逐步把它们接到真正的 case/app schema

### 2. 接 FastAPI 启动

目标：
- 应用启动时就能初始化 AI 使用的数据库连接
- 保证 vector schema 已经 ready

建议你先看：
- `backend/main.py`
- `backend/ai/runtime.py`
- `backend/ai/ingestion/vector_store.py`

你要做的结果应该类似：
- app startup 时创建 shared engine
- 调用 bootstrap
- 后续 route 可以直接用现有 AI 模块

### 3. 定义最小 `cases` 层

现在 AI 模块默认依赖这些字段：

- `claim_notice_at`
- `proof_of_claim_at`
- `last_deadline_alert_at`

你至少要把 case 这一层做成能支持：
- 上传一份 policy PDF
- 存一个 `case_id`
- 更新 claim dates
- 后续按 case 调 RAG

这里你要特别注意：
- `vector_documents.case_id` 现在还是字符串占位
- 如果你要把主表做成 UUID，也请和 Mingtao 先对齐

### 4. 接第二主线的事故数据流

这部分现在 Mingtao 已经先把共享契约定好了，但还没有接进真实 API。

你要看的文件：

- `backend/models/accident_types.py`
- `backend/ai/accident/report_payload_builder.py`
- `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md`

你后面要接的产品层入口，建议是：

- `POST /cases`
- `PATCH /cases/{case_id}/accident/stage-a`
- `PATCH /cases/{case_id}/accident/stage-b`
- `POST /cases/{case_id}/accident/report`
- `GET /cases/{case_id}/accident/report`

你在第二主线最重要的职责是：

- 存事故表单数据
- 调 builder 生成标准化 report payload
- 把 payload 交给 PDF generator
- 再把 report / summary 接到后面的 group chat room

### 5. 如果还有时间，再做日期/聊天入口

第二批建议你补：

- `PATCH /cases/{case_id}/claim-dates`
  - 更新 `claim_notice_at` / `proof_of_claim_at`
  - 触发 deadline checker

- 一个最小 chat route
  - 给未来 `handle_chat_event(...)` 接入口

## 你现在先不要花太多时间做的事

当前阶段不建议你优先投入：

- 完整 auth
- Stripe
- 很重的 deployment hardening
- 很复杂的 websocket room management
- 完整 production migration system

原因很简单：
现在最缺的不是“完整平台”，而是“能演示完整事故处理主线已经接进产品里”。

## 你和 Mingtao 的接口边界

默认分工是：

- Mingtao 管 `backend/ai/` 里的 AI core
- 你管 FastAPI、cases、app-layer route、shared DB wiring

如果你要改下面这些高协调文件，请先说一声：

- `backend/main.py`
- `backend/models/ai_types.py`
- `backend/.env.example`
- 共享 request/response schema
- `cases` 的主键类型和字段定义

## 你当前推荐分支

建议直接用：

```bash
git checkout main
git pull origin main
git checkout -b ke/backend-integration
git push -u origin ke/backend-integration
```

## 现在的协作规则

这个仓库当前不用 PR，走 branch-and-sync：

1. 从最新 `main` 开分支
2. 在你自己的分支开发
3. 每天至少 push 一次
4. 动高协调文件前先在群里说
5. 合回 `main` 前先 pull 最新 `main`
6. 本地跑检查再 push `main`

至少要跑：

```bash
cd backend
./.venv/bin/pytest
```

## 你完成后应该交付什么

当前阶段，希望你交出来的是：

- 一个稳定的 app-layer FastAPI 结构，不只是 demo route
- 一个最小 `cases` 方案
- 第二主线的事故 intake / report 相关 API
- upload / ask 继续可用，不要回退
- 给 Lou 的接口说明或样例 payload

如果你先把这些做好，项目就会从“RAG demo”变成“事故流程 + AI + 后续 chat 都能接上的产品雏形”。
