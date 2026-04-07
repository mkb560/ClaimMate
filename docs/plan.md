# ClaimMate 整体项目计划

## 1. 产品定位

ClaimMate 是一个面向普通车主的 AI-powered car insurance claims copilot。MVP 阶段优先聚焦 California car owners，帮助用户在车祸后更清楚地理解自己的保险条款、保存事故信息、跟进理赔进度，并在和保险公司/修车厂沟通时获得更有依据的 AI 辅助。

项目的核心差异化是：市面上很多 AI 理赔工具主要服务保险公司，提高 insurer 端的效率；ClaimMate 的定位是 consumer-side copilot，站在车主一侧，帮助非专业用户把复杂的 policy、claim rules、deadlines 和事故材料整理成可以行动的信息。

当前仓库仍是课程项目原型，不是生产级法律或保险服务。AI 输出只提供 general information，不提供法律意见、保险建议、责任认定或 settlement recommendation；所有关键回答都应尽量带 source citation 和 disclaimer。

## 2. 目标用户与使用场景

- 目标用户：在 California 发生车祸、需要处理 auto insurance claim 的普通车主。
- 典型痛点：看不懂 policy、事故现场不知道该收集什么、回家后材料整理困难、claim deadline 容易漏、和 adjuster / repair shop 沟通时缺少上下文。
- MVP 场景：用户上传 policy，完成事故 Stage A/B 信息收集，生成事故报告和 chat context，然后在 AI-assisted group chat 中继续跟进理赔。
- 商业方向：proposal 中的方向是 consumer-side per-case unlock，例如 `$4.99/case`；当前代码尚未实现 Stripe/payment，只作为产品路线参考。

## 3. 端到端产品链路

ClaimMate 的整体链路设计为：

```text
Policy Q&A
  -> Accident Stage A/B collection
  -> Accident report + chat-ready context
  -> AI-assisted claim group chat
  -> Deadline/dispute support and future paid case unlock
```

- Policy Q&A：用户上传 insurance policy，系统把它作为 KB-A；系统同时使用 curated California/regulatory sources 作为 KB-B，回答 coverage、policy facts、claim rules 等问题。
- Accident Stage A/B：事故现场先收集时间、地点、车牌、保险信息、照片、伤情/警察信息；回家后补充叙事、证人、repair/medical docs 等材料。
- Accident report/context：系统把 Stage A + Stage B 转成稳定的 report payload，并生成 chat-ready context，未来可用于 PDF 报告和 group chat pinned summary。
- AI-assisted group chat：用户可在 chat 中 `@AI` 提问；AI 根据 stage 1/2/3 调整语气，并在 dispute/deadline 场景中提供更中立、可引用的说明。

## 4. 三条产品主线

| 主线 | 用户价值 | 当前状态 | 下一步 |
| --- | --- | --- | --- |
| Policy Q&A / RAG | 帮用户理解 policy 和 California claim rules | 已实现 KB-A/KB-B 双源 RAG、policy upload、demo policy seed、policy status、citations、demo eval | 扩充 deterministic policy fact extraction、citation guard、更多 demo/eval questions |
| Accident Collection / Report | 帮用户结构化保存事故材料，减少遗漏 | 已实现 Stage A/B backend contract、accident API、report payload builder、fixed demo accident seed | Lou 继续完善 frontend form / report UX；后续接 PDF report file generation |
| AI-assisted Group Chat | 帮用户在 claim follow-up 中获得 AI 辅助和上下文衔接 | 已实现 `handle_chat_event`、stage-aware AI behavior、dispute/deadline triggers、chat message persistence、`room_bootstrap` | Ke 后续接 WebSocket room / invite link；Mingtao 继续增强 chat AI behavior |

## 5. 当前已实现状态

### AI / RAG

- User policy documents 作为 KB-A，curated regulatory/reference docs 作为 KB-B。
- `answer_policy_question(case_id, question)` 支持双源检索、回答和 inline `[S#]` citations。
- 常见 policy fact question 会先走 deterministic extractor，再 fallback 到 general RAG generation。
- dispute question 支持更窄的 KB-B regulatory retrieval，并带 stage-aware instruction；当前 dispute 回答还会附加 next-step helper，提示用户整理 denial/delay/amount dispute 相关材料和可追问保险公司的问题。
- 用户显式询问 claim deadlines / timelines 时，Deadline Explainer 会根据已保存的 claim dates 解释 15-day acknowledgment 和 40-day decision window；没有保存日期时会说明需要先补日期。
- 所有最终回答都附带固定 disclaimer。
- 已有 `run_demo_eval.py` 和 `run_chat_ai_eval.py`，用于固定 demo/eval 和 chat AI deterministic regression。

### App-layer Backend

- FastAPI app 已拆成 routers，包含 health、policy upload/ask、case creation、accident stage persistence、report generation、claim dates、chat event/messages、demo seed/status/catalog 等 endpoints。
- `GET /cases/{case_id}` 已返回 case snapshot，包括 accident JSON、claim dates、cached report/chat payloads，以及基于 `chat_context_json` 的 `room_bootstrap`。
- `case_chat_messages` 已支持 append-only chat timeline；`POST /cases/{case_id}/chat/event` 和简化版 `POST /cases/{case_id}/chat/messages` 会在 AI 有回复时写入 user/AI rows。
- `DELETE /cases/{case_id}` 已用于 demo cleanup。

### Accident Workflow

- 已定义 `StageAAccidentIntake`、`StageBAccidentIntake`、`AccidentReportPayload`、`AccidentChatContext` 等 shared contract。
- 已实现 deterministic report payload builder 和 chat context builder。
- 已实现 `POST /cases/{case_id}/demo/seed-accident` 和 `backend/scripts/seed_accident_demo.py`，方便 Lou 和 demo flow 使用固定事故数据。
- 尚未实现最终 PDF report file generation pipeline；当前是 report payload / preview 级别。

### Frontend / Demo UI

- `frontend/` 下已有 minimal Next.js demo UI。
- 当前 UI 已能展示 policy Q&A、demo policy flow、Stage A/B accident form、case snapshot、report preview 和 chat response demo。
- 前端完整 UX、最终 report/PDF 展示、business-facing polish 继续由 Lou 推进。

### Eval / Smoke / Docs

- `backend/scripts/run_demo_smoke.py` 已覆盖 live backend 路径：`health -> demo/policies -> seed-policy -> ask -> seed-accident -> case snapshot(room_bootstrap) -> chat/messages -> chat/event`。
- Backend CI 已跑 `pytest`，并额外运行 deterministic chat AI eval。
- `docs/` 已包含 demo、shared backend、frontend API examples、AI chat behavior contract、progress report 等文档。

## 6. 未实现 / 后续计划

以下内容不要描述成已完成，除非后续代码确实落地：

- Full authentication flows
- Stripe checkout / webhook / paid unlock
- Production deployment config and ops
- Database migrations for production schema management
- WebSocket room management
- Invite-link issuance / validation
- Final PDF report file generation and export pipeline
- Full case CRUD beyond current demo/product hooks
- Production-grade privacy, consent, observability, and abuse controls

## 7. 团队分工

### Mingtao Ding

- AI core and RAG
- Policy QA / citations / deterministic policy fact extraction
- Dispute detection and dispute-focused answer behavior
- Deadline tracking and reminder behavior
- Stage-aware chat AI behavior
- AI eval, smoke, and regression tests
- AI/backend integration contract docs

### Ke Wu

- FastAPI product/app layer
- Shared case persistence and database integration
- Chat backend persistence and room/product backend path
- Deployment, Stripe/payment, auth, and production integration targets
- Backend API cleanup and app-layer coordination

### Yi-Hsien Lou

- Frontend UI and UX
- Accident form and report preview experience
- PDF/report UX and business-facing presentation assets
- Demo frontend flow for policy Q&A, accident workflow, and chat

## 8. Roadmap

### Short Term

- Keep `main` stable and push owner work through `mingtao/dev`, `ke/...`, and `lou/...` style branches.
- Mingtao: Dispute Next-Step Helper 和 Deadline Explainer 已落地；下一步继续扩展 policy fact extraction、citation guard lite、真实 demo transcript 调优和 chat AI regression coverage。
- Ke: continue from HTTP chat persistence toward WebSocket room/invite-link architecture and production DB migration path.
- Lou: finish accident form polish, report preview/PDF UX, citation/chat timeline display, and final demo UI polish.

### Technical Milestone 1 Scope

- Show 20-40% of planned functionality through a working backend demo.
- Recommended demo path: health -> demo policies -> seed policy -> policy status -> policy Q&A -> regulatory Q&A -> optional accident/chat smoke.
- This demonstrates the technical foundation: policy ingestion, RAG, citations, deterministic demo assets, and AI chat behavior groundwork.

### Final Project Target

- End-to-end demo with policy Q&A, accident intake, report preview/export, chat timeline, AI answer/dispute/deadline support, and a clear consumer-side product story.
- Keep payment/auth/deployment scope realistic: if implemented, label clearly; otherwise present as roadmap.

## 9. AI 安全边界

- AI 不提供 legal advice、insurance advice、liability determination、medical advice 或 settlement recommendation。
- 对 injury、litigation、high-value claim、coverage denial 等高风险场景，AI 应建议用户咨询 licensed professional。
- AI 回答应尽量基于 policy/regulatory citations；没有足够依据时应保守 fallback。
- Stage 3 group chat 中 AI 使用 `For reference:` 语气，避免在有 adjuster/repair shop 的多方场景中显得替用户谈判或指责某一方。
- Deadline reminders 是基于 case date fields 的辅助提醒，不保证覆盖所有 legal deadlines。

## 10. Demo / Eval 命令

常用后端测试：

```bash
cd backend
./.venv/bin/pytest -q
```

固定 policy/RAG demo eval：

```bash
cd backend
DATABASE_URL=postgresql+psycopg://... OPENAI_API_KEY=... ./.venv/bin/python scripts/run_demo_eval.py
```

Chat AI deterministic eval：

```bash
cd backend
./.venv/bin/python scripts/run_chat_ai_eval.py --json-out /tmp/claimmate_chat_ai_eval.json
```

Live HTTP smoke：

```bash
cd backend
./.venv/bin/python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000
```

## 11. 文档阅读建议

- `docs/PROJECT_PROGRESS_AND_STRUCTURE.md`：当前仓库进度和结构快照。
- `docs/RUN_DEMO_ZH.md`：如何跑 demo 和 smoke。
- `docs/BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md`：后端 API 与 Lou 前端对接说明。
- `docs/YI_FRONTEND_API_EXAMPLE_ZH.md`：前端调用示例。
- `docs/AI_CORE_PLAN_ZH.md`：Mingtao AI core 详细子计划。
- `docs/AI_CHAT_BEHAVIOR_CONTRACT_ZH.md`：chat AI 触发、语气和行为契约。
