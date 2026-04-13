# ClaimMate 项目进度与仓库结构

本文档以根目录 [`README.md`](../README.md) 的产品愿景与分工为基准，**同步描述截至当前仓库的真实进度**（部分细节已比 README 中「最小 API」一节更新）。适合团队对齐状态与规划下一步。

---

## 产品愿景（三条主线）

与 README 一致，完整故事分为：

| 主线 | 内容 | 当前状态（摘要） |
|------|------|------------------|
| **1** | 双知识源 RAG（保单 KB-A + 法规 KB-B） | **最完整**：ingest、检索、grounded 回答、citations、争议/阶段化 chat 逻辑等在 `backend/ai/` 已落地 |
| **2** | 两阶段事故收集与报告 | **契约 + 后端 API + 存储**已接好；**前端 demo 已能读 snapshot / report**；**完整表单、PDF 成品文件**仍待做 |
| **3** | 理赔群聊中的 AI 支持 | **`handle_chat_event`、HTTP 与可选 WebSocket**；**JWT 注册登录、`AUTH_MODE`、case membership、invite 发放/兑换**；**`WS /ws/cases/{case_id}` 内存房间（原型）** — 详见 [`AUTH_AND_WEBSOCKET_KE.md`](AUTH_AND_WEBSOCKET_KE.md) |

项目定位仍是 **课程/原型**：AI core 与产品层后端已大幅打通，但**非**生产级平台（无完整 auth、计费、迁移体系等）。

---

## 已完成部分

### 1. 双知识源 RAG（主线 1）

- KB-A：用户上传的 policy PDF，chunk + 嵌入 + 按 `case_id` 检索  
- KB-B：California / U.S. 等法规与参考资料索引（见 `claimmate_rag_docs/`）  
- OpenAI + **pgvector** + SQLAlchemy AsyncEngine  
- 默认可用模型与维度策略见 README（如 `gpt-5.4-mini`、embedding 1536 维兼容表结构）  
- Citations、保单字段抽取、dispute / mention / deadline 等与 RAG 配套的 AI 模块  

**核心目录：** `backend/ai/ingestion/`、`backend/ai/rag/`、`backend/ai/policy/`，以及 `backend/ai/chat/`、`backend/ai/deadline/`、`backend/ai/dispute/` 等。

### 2. 第二主线：数据契约与报告中间层

- `StageAAccidentIntake` / `StageBAccidentIntake` / `AccidentReportPayload` / `AccidentChatContext`  
- 确定性 `report_payload_builder`（非 LLM 胡编结构）  

**核心文件：** `backend/models/accident_types.py`、`backend/ai/accident/report_payload_builder.py`  
**契约说明：** [`ACCIDENT_WORKFLOW_CONTRACT_ZH.md`](ACCIDENT_WORKFLOW_CONTRACT_ZH.md)

### 3. 应用层 FastAPI 与 `cases` 持久化

相对 README 中仅列三条路由的表述，当前后端已包含：

- **启动与 DB**：`lifespan` 中创建共享 engine；`bootstrap` 确保 **vector 表** + **`cases` 表**（含 `claim_notice_at`、`proof_of_claim_at`、`last_deadline_alert_at` 等，供 deadline 模块使用）  
- **路由分层**：`main.py` 负责应用组装；具体接口在 `backend/app/routers/`  
- **Policy + Ask（前端 demo 主路径）**  
  - `GET /health`  
  - `GET /demo/policies`
  - `GET /cases/{case_id}/policy`
  - `POST /cases/{case_id}/demo/seed-policy`
  - `POST /cases/{case_id}/policy`（`multipart/form-data`，字段名 `file`）  
  - `POST /cases/{case_id}/ask`（JSON `question`）  
- **事故流程 API**  
  - `POST /cases`  
  - `GET /cases/{case_id}`  
  - `POST /cases/{case_id}/demo/seed-accident`  
  - `PATCH /cases/{case_id}/accident/stage-a`  
  - `PATCH /cases/{case_id}/accident/stage-b`  
  - `POST /cases/{case_id}/accident/report`  
  - `GET /cases/{case_id}/accident/report`  
- **索赔日期与聊天入口**  
  - `PATCH /cases/{case_id}/claim-dates`  
  - `POST /cases/{case_id}/chat/event` → `chat_dispatch.chat_event_dispatch`（落库用户/AI 消息行）  
  - `GET /cases/{case_id}/chat/messages`、`POST /cases/{case_id}/chat/messages`（简化 `@AI` 发帖）  
  - `DELETE /cases/{case_id}` — 删除 case、聊天记录、membership/invite、该 case 的 KB-A 向量（最小 lifecycle / demo 重置）  
  - **Auth（可选）** — `POST /auth/register`、`POST /auth/login`、`GET /auth/me`；`AUTH_MODE` 控制 `/cases/*` 与 policy 路由是否要求 JWT + membership（默认 `off` 保持 demo/smoke）  
  - **Invite** — `POST /cases/{case_id}/invites`（owner）、`GET /invites/lookup`、`POST /auth/accept-invite`  
  - **WebSocket** — `WS /ws/cases/{case_id}?token=...` 房间内广播与可选 AI 派发（见 [`AUTH_AND_WEBSOCKET_KE.md`](AUTH_AND_WEBSOCKET_KE.md)）  

`GET /cases/{case_id}` 的 snapshot 含 **`room_bootstrap`**（来自事故报告写入的 `chat_context`），便于聊天区展示与 pinned 上下文。

**说明：** 上传的 PDF 会落在本地 `backend/.local_data/policies/{case_id}/`（便于开发与调试）。

### 4. 测试与联调支持

- 单元测试：`cd backend && pytest`（大量逻辑 mock，不强制本机 Postgres）  
- 可选集成测试：`pytest -m integration`，需真实 `DATABASE_URL`（Postgres + pgvector），见 `backend/tests/test_integration_cases_db.py`  
- demo policy seed：`python scripts/seed_demo_policy.py --case-id allstate-change-2025-05`，会把固定 demo PDF 索引进 KB-A  
- end-to-end smoke：`python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000`，会按真实 HTTP 路径跑 `health -> demo/policies -> seed-policy -> ask -> seed-accident -> room_bootstrap -> chat/messages -> chat/event`  
- 远程共享本机后端：`backend/scripts/run_shared_backend.sh`，说明见 [`REMOTE_SHARED_BACKEND_ZH.md`](REMOTE_SHARED_BACKEND_ZH.md)

### 5. 文档与前端对接说明

- 当前后端 / 前端对接汇总：[`BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md`](BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md)
- Lou 直接调用示例：[`YI_FRONTEND_API_EXAMPLE_ZH.md`](YI_FRONTEND_API_EXAMPLE_ZH.md)
- Mingtao AI chat 行为契约：[`AI_CHAT_BEHAVIOR_CONTRACT_ZH.md`](AI_CHAT_BEHAVIOR_CONTRACT_ZH.md)
- Demo 运行说明：[`RUN_DEMO_ZH.md`](RUN_DEMO_ZH.md)
- 文档索引：[`docs/README.md`](README.md)

---

## 仍需推进的部分

下列与 README「当前没有完全做完的部分」一致，并据**当前实现**稍作细化：

| 方向 | 说明 |
|------|------|
| **事故前端** | Stage A / B 表单、照片与报告预览等需与 API 字段对齐（见 accident 契约与 Lou 文档） |
| **PDF 事故报告文件** | 后端产出标准化 JSON；**生成可下载 PDF 文件**仍待接入 |
| **群聊产品层** | 后端已提供 **JWT + membership + invite + WS 房间（原型）**；前端免注册加入、与 pinned 报告完整串联仍依赖 Lou 侧产品化 |
| **支付 / Stripe** | 未在原型范围优先实现 |
| **完整部署与运维** | 无统一生产部署与监控方案 |
| **正式 case CRUD / DB 迁移** | 当前为开发友好型 `create_all` + 字符串 `case_id`；长期可演进 UUID、Alembic 等 |
| **端到端自动化** | 依赖 OpenAI 的 RAG 路径多以手工或 mock 测试为主，可按需增加带密钥的 E2E（谨慎成本） |

**若课程 demo 优先：** README 建议继续保证 **upload + ask 稳定**、**远程共享可用**、**演示问题与顺序固定**（见 [`DEMO_PLAYBOOK_ZH.md`](DEMO_PLAYBOOK_ZH.md)）。

---

## 当前仓库结构

与 README 顶层一致，下面补充 **backend** 内部与文档的细化树（省略 `.venv`/`venv`、`__pycache__`、`.pytest_cache` 等）：

```text
ClaimMate/
├── AGENTS.md
├── README.md
├── backend/
│   ├── main.py                 # FastAPI 入口：lifespan、CORS、挂载 routers
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── .env / .env.example     # 本地配置（勿提交密钥）
│   ├── ai/                     # AI 核心：ingestion、RAG、policy、chat、deadline、dispute、accident…
│   ├── app/                    # 应用层：case 服务、校验、路由子包 routers/
│   ├── models/                 # 共享模型：accident_types、ai_types、case_orm 等
│   ├── tests/                  # pytest（含 integration 标记用例）
│   ├── scripts/                # 索引、demo seed、smoke、共享后端等脚本
│   └── .local_data/            # 本地上传 policy 等（通常不提交大文件）
├── frontend/                   # Next.js demo UI：policy、snapshot、report、chat response 预览
├── claimmate_rag_docs/         # KB-B 法规/参考语料
├── demo_policy_pdfs/           # 演示用保单 PDF 样例
└── docs/                       # 方案、handoff、demo、本文档等
```

### 目录职责简述

| 路径 | 职责 |
|------|------|
| `backend/ai/` | RAG、嵌入、ingest、争议检测、deadline、chat AI、事故 report builder 等 **AI core** |
| `backend/app/` | **产品层**：`routers/`（health、policy/ask、cases/事故/claim-dates/chat）、`case_service`、`deps`、`paths` 等 |
| `backend/models/` | 与前后端/AI 共享的 **数据结构** 与 **Case ORM** |
| `backend/tests/` | 单元测试与可选 **真实 DB** 集成测试 |
| `backend/scripts/` | 运维与联调辅助脚本 |
| `frontend/` | 现有 Next.js demo UI，已能演示 policy Q&A 和 seeded accident/chat preview |
| `claimmate_rag_docs/` | KB-B 静态内容，**不要**与 demo 保单目录混索引 |
| `demo_policy_pdfs/` | KB-A 演示 PDF |
| `docs/` | 契约、进度、协作、运行说明 |

---

## 技术栈（与 README 一致）

- LLM / reasoning：`gpt-5.4-mini` 等（见 `.env.example`）  
- Embeddings：`text-embedding-3-large`，**1536 维** 写入以兼容 `pgvector(1536)`  
- 向量库：PostgreSQL + **pgvector**  
- 后端：**FastAPI**  
- DB：**SQLAlchemy** AsyncEngine + **psycopg**（异步 URL：`postgresql+psycopg://...`）  
- PDF：`pdfplumber`、`pypdf`；HTML：`html2text`；分词：`tiktoken`  

---

## 快速命令索引（摘自 README）

- 安装：`cd backend && pip install -e '.[dev]'`（或按 README 使用 `requirements.txt` + editable）  
- 启动：`uvicorn main:app --reload --host 0.0.0.0 --port 8000`（**工作目录应为 `backend`**，以便加载 `.env`）  
- 测试：`pytest`；集成：`pytest -m integration`  
- 更细步骤：[`RUN_DEMO_ZH.md`](RUN_DEMO_ZH.md)、根目录 [`README.md`](../README.md)  

---

## 团队分工（与 README 一致）

- **Mingtao Ding**：AI core、RAG、dispute、deadline、第二主线技术契约  
- **Ke Wu**：FastAPI 集成、case / app 层、chat 后端入口、部署相关协作  
- **Yi-Hsien Lou**：事故表单、前端体验、PDF/report UX、演示流程  

---

*若根目录 README 与本文件冲突，以本文件反映的**代码与路由**为准；流程与价值观仍以 README 为准。*
