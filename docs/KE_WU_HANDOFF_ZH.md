# 给 Ke 的开发说明

这份说明是给你当前阶段直接开工用的，不是长期架构文档。请先按这里的任务把 AI scaffold 接进可用的产品层。

## 你现在接手的项目状态

当前仓库里，AI 核心已经有了，但产品层还很薄。

- `backend/main.py` 现在只有 `/health`
- RAG、本地 policy ingest、KB-B indexing、dispute detection、deadline checker、chat AI scaffold 都已经在 `backend/ai/` 里
- 本地已经能用真实 PDF 跑问答，也能做 citations
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
4. 如果来得及，再补 claim dates 更新和 chat 入口

## 你第一阶段最该做的 4 件事

### 1. 接 FastAPI 启动

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

### 2. 定义最小 `cases` 层

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

### 3. 先做两个最小 API

第一批不要铺太大，先把 demo 路打通。

建议优先做：

- `POST /cases/{case_id}/policy`
  - 接收 policy 文件
  - 调 ingestion
  - 返回 ingest 结果

- `POST /cases/{case_id}/ask`
  - 接收用户问题
  - 调 `answer_policy_question(...)`
  - 返回 answer + citations

只要这两个能跑，Lou 那边就能先把 upload + ask 的 demo 页面接起来。

### 4. 如果还有时间，再做日期/聊天入口

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
现在最缺的不是“完整平台”，而是“能演示 AI 已经接进产品里”。

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

- 一个能启动的 FastAPI app，不只是 `/health`
- 一个可用的 upload policy endpoint
- 一个可用的 ask-AI endpoint
- 一个最小 `cases` 方案
- 给 Lou 的接口说明或样例 payload

如果你先把这几件事做好，整个项目就会从“AI scaffold”变成“可交互 demo”。
