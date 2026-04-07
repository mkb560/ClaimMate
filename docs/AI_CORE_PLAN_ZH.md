# ClaimMate — Mingtao Ding AI Core Plan

> 这是 Mingtao Ding 负责的 AI/RAG/dispute/deadline/chat behavior 子计划。团队级整体计划请先看 `docs/plan.md`。

## 背景

Mingtao 当前负责 ClaimMate 的 AI 核心部分：双知识源 RAG、dispute detection、deadline reminders，以及群聊中的 AI 行为。

这份文档是当前 `backend/` 目录下 AI Core MVP 脚手架的真实对齐版本，可以把它看成当前仓库里 AI 相关实现的“方案说明 + 同步记录”。

这版方案已经不再使用早期的 Qwen / DashScope 规划，而是收敛到：

- `OpenAI`
- `pgvector`
- `SQLAlchemy AsyncEngine`

并且范围明确收紧到课程项目 Phase 1 / MVP 原型。

**当前范围：**

- 对用户 policy PDF（KB-A）和 California / U.S. 法规资料（KB-B）做双知识源 RAG
- 两层 dispute detection
- 基于已存 claim dates 的被动 deadline reminder 与显式 Deadline Explainer
- Stage 1 / 2 / 3 群聊 AI 行为
- dispute 回答后的 next-step helper
- 固定 disclaimer + inline citations
- 第二主线的事故流程共享契约与报告 payload 中间层
- 固定 demo/eval 与 smoke 脚本，用来保护 AI/RAG/chat 行为不回退

**明确不在当前 Phase 1 范围内的内容：**

- 第二轮 hallucination validator
- 多 AI provider 抽象层
- DashScope / Qwen 相关部署逻辑
- 生产级别的 CCPA retention / observability 方案
- 生产级、大而全的 evaluation harness（当前只保留轻量 deterministic demo/eval）

---

## 最终技术栈

| 组件 | 当前选择 | 原因 |
|---|---|---|
| 主回答模型 | `gpt-5.4-mini` + `xhigh` reasoning | 适合 grounded QA 与较高强度的回答生成 |
| 分类模型 | `gpt-5.4-mini` + `xhigh` reasoning | 与主模型保持一致，减少行为差异 |
| Embeddings | `text-embedding-3-large`，按 1536 维写入 | 在保持较好检索质量的同时兼容当前 `pgvector(1536)` |
| 向量库 | PostgreSQL + `pgvector` | 方便和关系型 case 数据并存 |
| DB 接入 | 共享 `SQLAlchemy AsyncEngine` | 方便与 Ke 的 FastAPI app layer 对接 |
| Chunking | `tiktoken` | 简单直接的 token-aware chunking |
| PDF 解析 | `pdfplumber` + `pypdf` fallback | 兼顾表格和普通文本 |
| HTML 解析 | `html2text` | 对 KB-B 的 HTML 资料已经够用 |
| 存储 | 本地文件存储 + optional AWS S3 | 当前 demo/app route 主要使用 `.local_data/policies/`；S3 仅作为 object-storage ingestion 支持和 KB-B backup 可选项 |

**当前栈：**

`openai` + `pgvector` + `sqlalchemy[asyncio]` + `tiktoken` + `pdfplumber` + `pypdf` + `html2text` + `boto3`

---

## 当前文件结构

```text
backend/
├── pyproject.toml
├── requirements.txt
├── .env.example
├── main.py
├── models/
│   ├── __init__.py
│   ├── ai_types.py
│   ├── accident_types.py
│   └── case_orm.py
├── app/
│   ├── case_service.py
│   ├── demo_case_service.py
│   ├── demo_policy_service.py
│   ├── policy_service.py
│   └── routers/
│       ├── health.py
│       ├── policy_ask.py
│       └── cases_and_accident.py
├── ai/
│   ├── __init__.py
│   ├── clients.py
│   ├── config.py
│   │
│   ├── accident/
│   │   ├── __init__.py
│   │   └── report_payload_builder.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── pdf_parser.py
│   │   ├── html_parser.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── vector_store.py
│   │   ├── kb_b_loader.py
│   │   ├── kb_b_catalog.py
│   │   └── ingest_policy.py
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── prompt_templates.py
│   │   ├── citation_formatter.py
│   │   └── query_engine.py
│   │
│   ├── policy/
│   │   ├── __init__.py
│   │   └── fact_extractor.py
│   │
│   ├── dispute/
│   │   ├── __init__.py
│   │   ├── keyword_filter.py
│   │   └── semantic_detector.py
│   │
│   ├── deadline/
│   │   ├── __init__.py
│   │   └── deadline_checker.py
│   │
│   └── chat/
│       ├── __init__.py
│       ├── stage_router.py
│       ├── stage_prompts.py
│       ├── mention_handler.py
│       └── chat_ai_service.py
│
├── scripts/
│   ├── run_demo_eval.py
│   ├── run_chat_ai_eval.py
│   ├── run_demo_smoke.py
│   ├── seed_demo_policy.py
│   └── seed_accident_demo.py
│
└── tests/
```

---

## 当前已实现架构

```text
Policy PDF / Regulatory HTML or PDF
        │
   pdf_parser.py / html_parser.py
        │
   chunker.py (tiktoken)
        │
   embedder.py (OpenAI embeddings)
        │
   vector_store.py (SQLAlchemy + pgvector)
        │
   query_engine.py
        │
   gpt-5.4-mini
        │
   AnswerResponse with citations + disclaimer
```

### 存储模式

- `vector_store.py` 维护模块级别的 `async_sessionmaker`
- `init_engine(engine: AsyncEngine)` 在 FastAPI 启动时初始化一次
- `get_sessionmaker()` 给需要独立访问 DB 的 AI 模块使用
- `ensure_vector_schema(engine)` 在启动或 bootstrap 阶段负责创建 `vector` extension 和 AI 表
- 检索直接使用 `pgvector.sqlalchemy.VECTOR(...)` 和 `cosine_distance()`
- 当前没有使用 `raw asyncpg`，也没有第二个连接池

### 为什么选择共享 `AsyncEngine`，而不是单独 `asyncpg`

对这个项目来说，共享 `AsyncEngine` 是更合理的默认方案：

- Ke 的 app layer 后续本来也会用 SQLAlchemy + psycopg
- 如果再额外起一个 asyncpg pool，会增加连接管理复杂度
- `pgvector-python` 已经原生支持 SQLAlchemy
- 一个 engine 更容易做统一启动、统一 handoff、统一资源管理

只有在未来真正证明向量查询成为性能瓶颈时，才有必要考虑更底层的专门通道。

---

## 数据模型

### `vector_documents`

当前 AI scaffold 使用如下向量表。推荐的最终目标仍然是让 `vector_documents.case_id` 和 app-layer `cases.id` 保持完全一致；如果后续团队决定把 `cases.id` 改成 UUID 主键，则这里也应该最终改成 `UUID REFERENCES cases(id) ON DELETE CASCADE`。

当前之所以仍是字符串，是为了让 AI/RAG、demo case、脚本和 app-layer HTTP flow 在课程 demo 阶段保持低耦合、易调试。

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE vector_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     VARCHAR(64),
    source_type VARCHAR(8) NOT NULL CHECK (source_type IN ('kb_a', 'kb_b')),
    document_id VARCHAR(128),
    chunk_text  TEXT NOT NULL,
    page_num    INT,
    section     VARCHAR(256),
    embedding   vector(1536) NOT NULL,
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON vector_documents (source_type, case_id);
```

**当前 Phase 1 选择：**

暂时不做 ANN index。当前 chunk 数量不大，精确 cosine ordering 已经够用，而且更简单。

### `cases` 需要新增的字段

deadline module 当前默认依赖 `cases` 上有这些字段：

```sql
ALTER TABLE cases
ADD COLUMN claim_notice_at TIMESTAMPTZ NULL,
ADD COLUMN proof_of_claim_at TIMESTAMPTZ NULL,
ADD COLUMN last_deadline_alert_at TIMESTAMPTZ NULL;
```

**语义：**

- `claim_notice_at`：claim notice / report 提交或被 insurer 收到的时间
- `proof_of_claim_at`：触发 40-day decision clock 的材料提交时间
- `last_deadline_alert_at`：避免 24 小时内重复提醒的 cooldown 时间

### deadline integration contract

当前 app layer 已经有最小 `Case` ORM/table，并在本地/dev bootstrap 中创建 deadline 相关字段。`deadline_checker.py` 仍然保留原始 SQL 边界，这样可以继续和 app route、脚本、未来 migration 层低耦合。

这意味着 app layer 仍需要保证：

- 真实的 `cases` 表存在
- 上面的三个时间字段已经被创建或迁移进去
- 传给 AI 函数的 `case_id` 能够正确映射到 `cases.id`
- case 删除时，当前会清 DB rows、chat messages 和 vector rows；S3 / 本地 policy file lifecycle 属于后续协调项

---

## 第二主线共享契约

第二主线当前已经有共享技术骨架，但还没有接成完整产品流程。

当前已经存在：

- `StageAAccidentIntake`
- `StageBAccidentIntake`
- `AccidentReportPayload`
- `AccidentChatContext`
- `build_accident_report_payload(...)`
- `build_accident_chat_context(...)`

设计目的：

- 先把事故表单字段和事故报告中间层结构固定住
- 让 Ke 后面可以围绕这些 schema 接 API / 存储 / PDF generator
- 让 Lou 可以直接按共享字段做 Stage A / Stage B 表单与报告预览

详细说明见：

- `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md`

---

## KB-B 法规资料源

当前 MVP loader 索引下面这 6 份资料：

| ID | 文档 | URL | 格式 |
|---|---|---|---|
| `iso_pp_0001` | ISO Standard Auto Policy PP 00 01 | `https://doi.nv.gov/uploadedFiles/doinvgov/_public-documents/Consumers/PP_00_01_06_98.pdf` | PDF |
| `naic_model_900` | NAIC Model 900 | `https://content.naic.org/sites/default/files/model-law-900.pdf` | PDF |
| `naic_model_902` | NAIC Model 902 | `https://content.naic.org/sites/default/files/model-law-902.pdf` | PDF |
| `ca_fair_claims` | CA Fair Claims Settlement Regulations | `https://www.insurance.ca.gov/01-consumers/130-laws-regs-hearings/05-CCR/fair-claims-regs.cfm` | HTML |
| `iii_nofault` | No-Fault vs At-Fault Reference | `https://www.iii.org/article/background-on-no-fault-auto-insurance` | HTML |
| `naic_complaints` | NAIC Complaint Data | `https://content.naic.org/cis_agg_reason.htm` | HTML |

实现说明：

- `kb_b_loader.py` 顺序下载并索引这些资料
- 如果配置了 S3，也可以顺手备份
- 当前本地仓库也支持直接从 `claimmate_rag_docs/` 做 KB-B 索引

---

## Chunking 策略

**KB-A（policy PDF）：**

- `500` token chunk
- `50` token overlap
- 如果可能，从大写标题推断 `section`
- 表格尽量转成 markdown
- metadata 包含 `case_id`、`page_num`、`section`

**KB-B（regulatory docs）：**

- `250` token chunk
- `30` token overlap
- 如果可能，从类似 `§2695.5` 的标题推断 `section`
- metadata 包含 `document_id`、`page_num`、`section`

---

## RAG 查询流程

```text
User question
    │
    ├── 用 text-embedding-3-large（1536 维）向量化问题
    ├── 按 case_id 搜 KB-A
    └── 在共享法规语料里搜 KB-B
             │
      build <policy_context> + <regulatory_context>
             │
          gpt-5.4-mini
             │
    parse [S1], [S2] inline citations
             │
    return AnswerResponse + fixed disclaimer
```

### grounding 规则

- 回答只能来自检索到的 chunk
- 如果检索结果为空或不足以支持回答，要明确说信息不足
- 每个事实性句子都要带 `[S#]`
- 用户最终看到的答案必须以固定 disclaimer 结尾：

```text
Disclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.
```

### 当前 Phase 1 简化

当前 scaffold 没有 `response_validator.py` 这类 second-pass hallucination check。

现在的 grounding 主要靠：

- prompt 限制
- 收紧后的检索上下文
- inline citation parser
- source 不足时的保守 fallback

---

## Prompt 设计

### `SYSTEM_PROMPT_RAG`

- 只能根据 `<policy_context>` 和 `<regulatory_context>` 回答
- 如果证据不够，就明确说 `not enough information`
- 事实性内容后面加 `[S#]`
- 不能给法律意见或 settlement recommendation

### `SYSTEM_PROMPT_DISPUTE`

- 解释事实性权利和 next steps
- 必须 grounded 在 policy / regulation 文本里
- 不替用户做 accept / reject 决定
- 在多人房间里保持中性

### citation 格式

当前实现要求模型输出这类 inline citation：

```text
Your deductible is $500. [S1]
California requires acknowledgment within 15 days. [S2]
```

这个格式比自由文本的 `[Source: ...]` 更容易生成，也更容易解析。

---

## Dispute Detection

### 第 1 层：keyword filter

实现文件：`keyword_filter.py`

**硬触发词：**

- `denied my claim`
- `claim denied`
- `bad faith`
- `underpaid`
- `refuse to pay`
- `wrong amount`
- `rejection letter`

**软触发词：**

- `disagree`
- `too low`
- `not fair`
- `no response`
- `delay`
- `ignored`

软触发当前至少需要 2 个命中才升级。

### 第 2 层：semantic classifier

实现文件：`semantic_detector.py`

- 模型：`gpt-5.4-mini`
- 输出格式：JSON
- 标签：`DENIAL | DELAY | AMOUNT | OTHER | NOT_DISPUTE`

当前代码里的法规映射：

- `DENIAL` → `10 CCR §2695.7(b)`
- `DELAY` → `10 CCR §2695.5(e)` / `§2695.7(c)`
- `AMOUNT` → `10 CCR §2695.8`
- `OTHER` → `10 CCR §2695`

一旦 dispute 被确认，服务会切换到 dispute-focused RAG，使用 policy chunks 加筛过的法规资料一起回答。

---

## Deadline Tracker

旧版基于 `activated_at` / Stripe 的 deadline 设计已经不再使用。

### 当前 MVP 模型

- `claim_notice_at` 触发 15-calendar-day acknowledgment reminder
- `proof_of_claim_at` 触发 40-day decision reminder
- reminder 是被动的、信息型的
- 通过 `last_deadline_alert_at` 做 24 小时冷却
- 用户用 `@AI` 明确询问 deadline / timeline / due date 时，会走显式 Deadline Explainer

### 当前使用的 California 时间模型

- claim notice date 后 15 calendar days 提醒
- proof-of-claim date 后 40 days 提醒

AI **不会**从聊天文本中自动推断法律日期，也**不会**在日期可能不完整时做强结论。

### 当前 reminder / explainer 风格

当前 deadline reminder 会明确说明：它是基于已保存的 case dates 生成的，如果日期不完整，用户需要先更新。

显式 Deadline Explainer 也只基于已保存的 `claim_notice_at` / `proof_of_claim_at` 计算窗口；它不更新 `last_deadline_alert_at`，因此不会影响被动 deadline reminder 的 cooldown。

---

## Group Chat AI Stages

### Stage 路由

实现文件：`stage_router.py`

```python
def determine_stage(participants: list[Participant], invite_sent: bool) -> ChatStage:
    roles = {participant.role for participant in participants}
    has_external = "adjuster" in roles or "repair_shop" in roles

    if has_external:
        return ChatStage.STAGE_3
    if invite_sent:
        return ChatStage.STAGE_2
    return ChatStage.STAGE_1
```

### 当前各 Stage 行为

| Stage | 条件 | 当前行为 |
|---|---|---|
| `STAGE_1` | 只有 owner | 一次性的 `policy indexed` proactive summary，加 `@AI` 问答 |
| `STAGE_2` | 只有 owner，但 invite 已发 | `@AI` 问答 + dispute/deadline 响应，减少主动插话 |
| `STAGE_3` | 有外部参与者加入 | 语气中性，回答前缀 `For reference:` |

### Mention handling

实现文件：`mention_handler.py` 和 `chat_ai_service.py`

行为：

1. 检测 `@AI` 或 `@ai`
2. 提取 mention 之后的问题文本
3. 如果文本为空，让用户补问题
4. 如果是明确 deadline / timeline / due date 问题，走 Deadline Explainer
5. 否则跑 dispute detection
6. 如果 dispute confirmed，就走 dispute-focused RAG，并附 next-step helper
7. 否则走普通 policy question RAG
8. 如果在 Stage 3，回答前加 `For reference:`

### 非 mention 行为

如果一个事件没有触发更高优先级的 proactive / mention / dispute 响应，那么最后的 fallback 是 deadline reminder（如果当前到了该提醒的时间）。

---

## 对外公共接口

下面这些 AI core 函数目前通过 `backend/ai/__init__.py` 暴露：

```python
def init_engine(engine: AsyncEngine) -> None
async def ingest_policy(s3_key: str, case_id: str) -> None
async def answer_policy_question(case_id: str, question: str) -> AnswerResponse
async def handle_chat_event(event: ChatEvent) -> AIResponse | None
async def on_claim_dates_updated(
    case_id: str,
    claim_notice_at: datetime | None,
    proof_of_claim_at: datetime | None,
) -> None
```

### 共享类型

共享类型当前分两组：

- `backend/models/ai_types.py`
- `backend/models/accident_types.py`

`ai_types.py` 里的关键枚举和 dataclass：

- `ChatStage`
- `AITrigger`
- `ChatEventTrigger`
- `Participant`
- `Citation`
- `AnswerResponse`
- `AIResponse`
- `ChatEvent`

`ChatEvent` 当前仍然包含：

- `case_id`
- `sender_role`
- `message_text`
- `participants`
- `invite_sent`
- `trigger`
- 可选 `metadata`
- 可选 `occurred_at`

`accident_types.py` 里的关键类型：

- `StageAAccidentIntake`
- `StageBAccidentIntake`
- `AccidentReportPayload`
- `AccidentChatContext`
- `PartyRecord`
- `PhotoAttachment`

---

## 环境变量

当前 `AIConfig` 的形状如下：

```python
openai_api_key: str = ""
openai_base_url: str = "https://api.openai.com/v1"
rag_model: str = "gpt-5.4-mini"
rag_reasoning_effort: str = "xhigh"
classification_model: str = "gpt-5.4-mini"
classification_reasoning_effort: str = "xhigh"
embedding_model: str = "text-embedding-3-large"
cors_allow_origins: str = ...
cors_allow_origin_regex: str = ...
database_url: str = ""

aws_access_key_id: str = ""
aws_secret_access_key: str = ""
s3_bucket_name: str = ""
aws_region: str = "us-east-1"

vector_table_name: str = "vector_documents"
vector_dimensions: int = 1536

kb_a_chunk_size: int = 500
kb_a_chunk_overlap: int = 50
kb_b_chunk_size: int = 250
kb_b_chunk_overlap: int = 30
rag_top_k_per_source: int = 4
deadline_alert_threshold_days: int = 5
deadline_alert_cooldown_hours: int = 24
```

启动模板见：

- `backend/.env.example`

---

## 依赖

当前后端依赖包括：

```text
fastapi
openai
pgvector
sqlalchemy[asyncio]
psycopg[binary]
pydantic-settings
tiktoken
pdfplumber
pypdf
html2text
boto3
requests
uvicorn
pytest
pytest-asyncio
```

当前没有使用：

- LangChain
- LlamaIndex
- DashScope

---

## 测试状态

当前 scaffold 已经有确定性测试覆盖：

- stage routing
- dispute keyword filtering
- semantic dispute fallback behavior
- deadline calculation
- deadline message formatting / cooldown behavior
- `@AI` mention extraction
- citation parsing / fallback
- chat service routing behavior
- deterministic chat AI eval
- accident payload contract
- main upload / ask API
- demo seed / smoke helpers

当前本地验证命令：

```bash
cd backend
./.venv/bin/pytest -q
./.venv/bin/python scripts/run_chat_ai_eval.py --json-out /tmp/claimmate_chat_ai_eval.json
./.venv/bin/python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000
```

不要在文档里写死旧的测试数量；以本地 `pytest` / CI 输出为准。当前 Backend CI 也会运行 deterministic chat AI eval，用来保护 Mingtao 负责的 chat behavior 不回退。

`run_demo_smoke.py` 需要一个正在运行的本地或 shared backend；`run_chat_ai_eval.py` 不依赖真实 OpenAI 调用或 live DB。

---

## 剩余集成任务

### Ke Wu / app integration

当前已完成：

- FastAPI app bootstrap、router include、CORS 与健康检查
- 最小 `cases` ORM/table、deadline fields、本地/dev bootstrap
- policy upload / ask / demo seed / policy status routes
- Stage A / Stage B / report / claim-dates routes
- chat event/messages persistence 与 `room_bootstrap`
- demo case delete cleanup for DB rows, vectors, and chat messages

仍需协调或后续实现：

- 生产级 migration 与最终 case ID/type 决策
- 生产 deployment、auth、invite link、WebSocket room、Stripe
- 外部 S3 / 本地 policy file lifecycle 的最终清理策略
- shared API contract 变更时同步 tests、docs、frontend handoff

### Mingtao 当前还能继续做什么

- 扩展 deterministic eval datasets（`run_demo_eval.py`、`run_chat_ai_eval.py`）
- 继续补 semantic dispute / deadline / citation regression tests
- 用真实 demo transcript 调整 prompt、RAG fallback、stage-specific tone
- 保持 AI behavior contract docs 与实际 chat behavior 同步
- shared API 影响 AI behavior 时，补短 handoff 文档和 smoke/eval 覆盖

---

## 重要假设

- 当前 MVP 只使用 OpenAI
- policy ingestion 当前既支持 S3，也支持本地文件
- KB-B 备份上传到 S3 是可选的
- AI core 和 app ORM 仍保持低耦合；后续 schema/API 变动需要同步 tests、docs 和 smoke/eval
- deadline reminder 是信息型的、基于日期字段的，不是从聊天自动推断的

---

## 参考资料

- [OpenAI API Pricing](https://openai.com/api/pricing)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [pgvector Python SQLAlchemy support](https://github.com/pgvector/pgvector-python)
- [California Fair Claims Regulations](https://www.insurance.ca.gov/01-consumers/130-laws-regs-hearings/05-CCR/fair-claims-regs.cfm)
- [California DOI claim timing guide](https://www.insurance.ca.gov/0200-industry/0050-renew-license/0200-requirements/upload/Guide-for-Adjusting-Property-Claims-in-California-After-a-Major-Disaster.pdf)
