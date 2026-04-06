# ClaimMate

ClaimMate 是一个面向车主的 AI 理赔助手原型项目。它的目标不是站在保险公司一侧优化流程，而是站在投保人一侧，帮助用户理解保单、梳理事故材料、跟踪理赔时限，并在后续沟通中提供有依据的 AI 支持。

当前这个仓库已经不是单纯的想法文档，而是一个可运行的后端原型：

- 支持上传真实 policy PDF
- 支持基于保单和法规做双知识源 RAG 问答
- 支持返回 grounded answer + citations
- 支持 `cases` 持久化、事故双阶段 intake、报告 JSON 生成
- 支持 claim dates 更新和 chat-event 入口调用 AI orchestration
- 支持一个最小 Next.js demo UI 去演示 policy Q&A、事故 snapshot、报告预览和 chat response
- 支持本地 `pgvector` 向量检索
- 支持通过临时公网地址把你本机后端共享给远程队友联调

不过它还不是完整生产产品。更准确地说，它现在是“AI core 已经打通、产品层正在继续接”的课程项目原型。

## 项目目标

ClaimMate 的完整产品故事有三条主线：

1. 双知识源 RAG
2. 两阶段事故信息收集与报告生成
3. 后续理赔群聊中的 AI 支持

当前仓库里，第一条主线已经最完整；第二条主线已经不只是 contract，而是连同 app-layer API 和本地持久化一起接上了；第三条主线的 AI 逻辑模块和 HTTP 入口已经存在，但完整的群聊产品层还没有完全接起来。

## 当前已经实现了什么

### 1. Dual-Knowledge RAG

后端现在支持：

- `KB-A`：用户上传的保单 PDF
- `KB-B`：California / U.S. 相关法规与参考资料
- 基于 `OpenAI + pgvector + SQLAlchemy AsyncEngine` 的检索链路
- 基于 `gpt-5.4-mini` 的 grounded answer generation
- 引用来源展示（citations）
- 保单字段的确定性抽取优先于普通生成式回答

相关核心代码在：

- `backend/ai/ingestion/`
- `backend/ai/rag/`
- `backend/ai/policy/`

### 2. 第二主线：契约 + API + 报告中间层

事故流程的共享技术契约已经先落地，包括：

- `StageAAccidentIntake`
- `StageBAccidentIntake`
- `AccidentReportPayload`
- `AccidentChatContext`
- 事故数据到标准化报告 payload 的确定性 builder

相关代码在：

- `backend/models/accident_types.py`
- `backend/ai/accident/report_payload_builder.py`
- `backend/app/accident_codec.py`
- `backend/app/case_service.py`
- `backend/app/routers/cases_and_accident.py`

当前已经能做的不是只有“定 schema”，还包括：

- `POST /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/demo/seed-policy`
- `POST /cases/{case_id}/demo/seed-accident`
- `PATCH /cases/{case_id}/accident/stage-a`
- `PATCH /cases/{case_id}/accident/stage-b`
- `POST /cases/{case_id}/accident/report`
- `GET /cases/{case_id}/accident/report`

现在后端可以把 Stage A / Stage B JSON 存进 `cases` 表，并生成事故报告 payload 与 chat context 的 JSON 结果，方便 Lou 直接接表单和报告预览。

### 3. 当前后端 API

当前 FastAPI 已经不只是最小 demo 路由，而是包含一层轻量 app-layer：

- `GET /health`

RAG / demo 主路径：

- `GET /demo/policies`
- `GET /cases/{case_id}/policy`
- `POST /cases/{case_id}/demo/seed-policy`
- `POST /cases/{case_id}/policy`
- `POST /cases/{case_id}/ask`

事故与 case：

- `POST /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/demo/seed-accident`
- `PATCH /cases/{case_id}/accident/stage-a`
- `PATCH /cases/{case_id}/accident/stage-b`
- `POST /cases/{case_id}/accident/report`
- `GET /cases/{case_id}/accident/report`
- `PATCH /cases/{case_id}/claim-dates`

聊天 AI 入口：

- `POST /cases/{case_id}/chat/event`

也就是说，前端现在不仅可以围绕“上传保单 + 提问 + 展示 AI 回答”这条 demo 路联调，也可以开始对接事故流程、报告预览、claim date 更新和 chat-event 触发。

### 4. 当前前端 demo UI

仓库里现在也已经有一个最小 Next.js demo 前端：

- `frontend/src/app/page.tsx`
- `frontend/src/lib/api.ts`

它当前可以直接演示：

- `/health`
- demo policy catalog
- indexed policy status
- policy upload + ask
- seeded accident demo case
- `GET /cases/{case_id}` snapshot 读取
- accident report JSON preview
- stage 3 chat event response + citations

### 5. 远程共享后端

如果队友不在同一地点，也不想各自本地重建 RAG，可以直接连接你这台机器已经跑好的后端。

仓库里已经提供：

- `backend/scripts/run_shared_backend.sh`
- `backend/scripts/seed_demo_policy.py`
- `backend/scripts/run_demo_smoke.py`
- `docs/REMOTE_SHARED_BACKEND_ZH.md`

它会用 `ngrok` 把你本机的 `FastAPI` 服务暴露成临时公网地址，方便 Ke 和 Lou 直接联调。

## 当前没有完全做完的部分

下面这些能力在 proposal 里有，但当前仓库还没有完全落地：

- 完整事故表单前端流程
- 真正的 PDF 事故报告生成文件
- 完整 chat room / WebSocket 产品层
- invite link 免注册加入房间
- payment / Stripe
- 完整部署体系
- 完整 case CRUD、正式数据库迁移和长期 schema 演进

所以请把当前项目理解成：

- 已经可运行的 AI 后端原型
- 已经可 demo 的 upload + ask 链路
- 已经有 app-layer 的 case / accident / claim-dates / chat-event 接口骨架
- 正在继续往完整产品故事靠拢

## 仓库结构

```text
ClaimMate/
├── AGENTS.md
├── README.md
├── backend/
├── frontend/
├── claimmate_rag_docs/
├── demo_policy_pdfs/
└── docs/
```

### `backend/`

核心后端代码都在这里：

- `main.py`：FastAPI 入口
- `ai/`：AI 核心逻辑
- `app/`：应用层路由、case service、请求校验、本地文件路径
- `models/`：共享数据结构
- `tests/`：自动化测试
- `scripts/`：本地索引、查询、demo、共享后端脚本

### `frontend/`

最小 Next.js demo UI，当前用于：

- health check
- policy upload / ask
- accident case snapshot preview
- report/chat demo response 展示

### `claimmate_rag_docs/`

本地 KB-B 法规与参考资料目录，用来做 regulatory corpus 索引。

### `demo_policy_pdfs/`

仓库内自带的 demo policy PDF 样例。它们是给 KB-A / demo 用的，不应该和 `claimmate_rag_docs/` 混在一起索引。

当前也已经有一条稳定的 demo seed 路径：

- `POST /cases/{case_id}/demo/seed-policy`

以及两个配套读接口：

- `GET /demo/policies`
- `GET /cases/{case_id}/policy`

它会把固定 demo PDF 复制到本地 policy 存储目录并索引进 KB-A。对 3 个内建 demo case：

- `allstate-change-2025-05`
- `allstate-renewal-2025-08`
- `progressive-verification-2026-03`

可以直接用对应 `case_id` 调用，不需要再手动上传 PDF。

如果前端或 demo 页面需要在刷新后恢复当前状态，可以用 `GET /cases/{case_id}/policy` 读取当前是否已经有 KB-A policy、当前文件名、chunk 数量，以及它是否匹配某个内建 demo policy。

### `docs/`

项目文档、联调说明、协作规则、demo 说明、handoff 文件都放在这里。

## 当前技术栈

- LLM：`gpt-5.4-mini`
- Embeddings：`text-embedding-3-large`（按 1536 维写入，兼容当前 `pgvector(1536)`）
- 向量库：PostgreSQL + `pgvector`
- 后端：FastAPI
- ORM / DB 接入：SQLAlchemy AsyncEngine + psycopg
- PDF 解析：`pdfplumber` + `pypdf`
- HTML 解析：`html2text`
- Token chunking：`tiktoken`

## 快速开始

### 1. 启动 pgvector

```bash
docker pull --platform linux/arm64 pgvector/pgvector:pg16
docker run -d --platform linux/arm64 \
  --name claimmate-pgvector \
  -e POSTGRES_USER=claimmate \
  -e POSTGRES_PASSWORD=claimmate \
  -e POSTGRES_DB=claimmate \
  -p 5433:5432 \
  pgvector/pgvector:pg16
```

### 2. 安装依赖

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install -e '.[dev]'
```

### 3. 配置环境变量

最小需要：

```bash
export OPENAI_API_KEY="your_key"
export DATABASE_URL="postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
```

### 4. 启动后端

```bash
cd backend
./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 6. Seed demo 保单或手动上传后提问

```bash
curl "http://127.0.0.1:8000/demo/policies"

curl -X POST "http://127.0.0.1:8000/cases/allstate-change-2025-05/demo/seed-policy"

curl "http://127.0.0.1:8000/cases/allstate-change-2025-05/policy"

curl -X POST "http://127.0.0.1:8000/cases/demo-case/policy" \
  -F "file=@/absolute/path/to/policy.pdf"

curl -X POST "http://127.0.0.1:8000/cases/allstate-change-2025-05/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Who are the policyholders and what is the policy number?"}'
```

如果你想把某个固定 demo PDF 种到自定义 `case_id`，也可以显式传 `policy_key`：

```bash
curl -X POST "http://127.0.0.1:8000/cases/demo-policy-case/demo/seed-policy" \
  -H "Content-Type: application/json" \
  -d '{"policy_key":"progressive-verification"}'
```

更完整的本地 demo 运行方式见：

- `docs/RUN_DEMO_ZH.md`

### 6.5. 一键跑完整 smoke flow

如果你想确认当前后端从 `health -> demo/policies -> seed-policy -> ask -> seed-accident -> case snapshot(room_bootstrap) -> chat/messages -> chat/event` 这条整链都还是通的，可以直接跑：

```bash
cd backend
./.venv/bin/python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000
```

如果你想直接检查 shared backend，也可以把 `--base-url` 换成当前 ngrok 地址。

### 7. 创建 case、写入事故信息、生成报告

```bash
curl -X POST "http://127.0.0.1:8000/cases" \
  -H "Content-Type: application/json" \
  -d '{"case_id":"demo-case"}'

curl -X PATCH "http://127.0.0.1:8000/cases/demo-case/accident/stage-a" \
  -H "Content-Type: application/json" \
  -d '{"quick_summary":"Rear-end collision at a red light.","police_called":true}'

curl -X PATCH "http://127.0.0.1:8000/cases/demo-case/accident/stage-b" \
  -H "Content-Type: application/json" \
  -d '{"detailed_narrative":"Stopped at a light and got hit from behind.","damage_summary":"Rear bumper damage."}'

curl "http://127.0.0.1:8000/cases/demo-case"

curl -X POST "http://127.0.0.1:8000/cases/demo-case/accident/report"
```

### 8. 更新 claim dates 和触发 chat event

```bash
curl -X PATCH "http://127.0.0.1:8000/cases/demo-case/claim-dates" \
  -H "Content-Type: application/json" \
  -d '{"claim_notice_at":"2026-04-01T10:00:00Z","proof_of_claim_at":"2026-04-03T10:00:00Z"}'

curl -X POST "http://127.0.0.1:8000/cases/demo-case/chat/event" \
  -H "Content-Type: application/json" \
  -d '{"sender_role":"owner","message_text":"@AI what does my policy say about rental reimbursement?","participants":[{"user_id":"u1","role":"owner"}],"invite_sent":false,"trigger":"message","metadata":{}}'
```

## 共享给远程队友

如果 Ke 和 Lou 不想自己本地起 RAG，可以直接连你这台机器的后端。

使用：

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
./scripts/run_shared_backend.sh
```

更多说明见：

- `docs/REMOTE_SHARED_BACKEND_ZH.md`

## 测试

当前后端测试命令：

```bash
cd backend
./.venv/bin/pytest
```

如果你要做一轮更贴近 demo 的 HTTP smoke：

```bash
cd backend
./.venv/bin/python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000
```

如果你本地已经配好真实 `DATABASE_URL`，还可以跑集成测试：

```bash
cd backend
DATABASE_URL=postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate ./.venv/bin/pytest -m integration
```

## 团队分工

- Mingtao Ding：AI core、RAG、dispute、deadline、第二主线技术契约
- Ke Wu：FastAPI integration、case/app layer、chat backend、deployment
- Yi-Hsien Lou：事故表单、前端体验、PDF/report UX、演示流程

## 重要文档入口

- 文档索引：`docs/README.md`
- 详细 AI 方案：`docs/plan.md`
- 第二主线契约：`docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md`
- 本地 demo 运行：`docs/RUN_DEMO_ZH.md`
- 远程共享后端：`docs/REMOTE_SHARED_BACKEND_ZH.md`
- Ke handoff：`docs/KE_WU_HANDOFF_ZH.md`
- Lou handoff：`docs/YI_HSIEN_LOU_HANDOFF_ZH.md`

## 当前最适合继续做的事

如果你们接下来继续按 proposal 推进，最优先的是：

1. 把第二主线的事故表单和报告生成接进产品层
2. 把第三主线的 chat room / invite link 接起来
3. 把现有 AI 后端从 demo 形态继续收成完整用户旅程

如果只是先准备课程 demo，那最优先的是：

1. 保证 upload + ask 稳定
2. 保证远程共享地址可用
3. 固定演示问题和展示顺序
