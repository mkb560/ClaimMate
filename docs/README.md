# 文档索引

这个目录集中存放 ClaimMate 的项目进度、协作说明、demo 运行方式、接口 handoff 和 milestone 录制材料。仓库根目录的 `README.md` 是项目总说明；根目录的 `AGENTS.md` 继续保留给 coding agents 使用。

## 推荐阅读顺序

1. `plan.md`：团队级整体项目计划、产品定位、三条主线和 roadmap。
2. `PROJECT_PROGRESS_AND_STRUCTURE.md`：当前真实进度、API 范围和仓库结构。
3. `RUN_DEMO_ZH.md`：本地/共享后端 demo 怎么跑。
4. `BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md`：当前后端接口与前端对接说明。
5. `YI_FRONTEND_API_EXAMPLE_ZH.md`：前端调用 policy / accident / report / chat API 的示例。
6. `AI_CORE_PLAN_ZH.md`：Mingtao AI core / RAG / dispute / deadline / chat behavior 子计划。
7. `AI_CHAT_BEHAVIOR_CONTRACT_ZH.md`：Mingtao 负责的 AI chat 行为契约。
8. `AUTH_AND_WEBSOCKET_KE.md`：JWT、`AUTH_MODE`、invite、WebSocket 房间（需要时阅读）。
9. `TEAM_SYNC_AUTH_WEBSOCKET_KE_ZH.md`：**给 Lou / Mingtao 的同步说明**（如何用 Ke 的 auth / invite / WS 更新）。

## 项目与协作

- `plan.md`：团队级整体项目计划，覆盖产品定位、三条主线、团队分工和 roadmap。
- `AI_CORE_PLAN_ZH.md`：Mingtao AI core 详细子计划，保留原 AI Core MVP 方案细节。
- `PROJECT_PROGRESS_AND_STRUCTURE.md`：基于当前代码整理的进度、待办方向与仓库结构。
- `CONTRIBUTING.md`：团队协作规则、分支规范和本地检查要求。
- `TEAM_TASKS.md`：当前任务拆分和协作优先级说明。
- `TEAM_SYNC_AUTH_WEBSOCKET_KE_ZH.md`：Auth / Invite / WebSocket 更新同步（Lou & Mingtao）。
- `progress_report_en.md`：英文阶段进度报告。

## Demo 与运行

- `RUN_DEMO_ZH.md`：从零启动 demo、seed demo data、跑 smoke/eval 的完整说明。
- `DEMO_PLAYBOOK_ZH.md`：固定 demo 路径、问题顺序和展示重点。
- `REMOTE_SHARED_BACKEND_ZH.md`：把本机后端通过公网共享给远程队友的说明。
- `ACCIDENT_CHAT_DEMO_ASSETS_ZH.md`：固定事故流程与 chat demo 资产、脚本和样例输出。

## 接口与行为契约

- `TEAM_SYNC_AUTH_WEBSOCKET_KE_ZH.md`：面向 Lou / Mingtao 的同步与接入手册（与 `AUTH_AND_WEBSOCKET_KE.md` 配套）。
- `AUTH_AND_WEBSOCKET_KE.md`：JWT 与 `AUTH_MODE`、case membership、invite、WebSocket 房间（Ke 落地说明）。
- `BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md`：当前 app-layer backend API、policy/事故/chat 流程和 Lou 前端接法。
- `YI_FRONTEND_API_EXAMPLE_ZH.md`：给 Lou 的前端直接调用示例，覆盖 demo policy catalog、policy status、case snapshot、report、chat event/messages。
- `ACCIDENT_WORKFLOW_CONTRACT_ZH.md`：第二主线 Stage A/B、report payload、chat context 的共享技术契约。
- `AI_CHAT_BEHAVIOR_CONTRACT_ZH.md`：Mingtao 负责的 AI chat 触发规则、stage 语气、response 字段和回归检查说明。

## Milestone 录制材料

- `TECHNICAL_MILESTONE_1_VIDEO_SCRIPT.md`：Technical Milestone 1 录屏操作与英文讲稿。
- `BUSINESS_MILESTONE_1_VIDEO_SCRIPT.md`：Business Milestone 1 动画视频英文讲稿与 PPT 展示建议。

## 已收口的旧文档

- 早期 Ke 最小 API 契约和阶段 handoff 已被当前 app-layer 实现和 `BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md` 覆盖，已从 `docs/` 删除，避免继续引用旧接口范围。
- 早期 Lou 阶段 handoff 已被当前 `BACKEND_INTEGRATION_SUMMARY_AND_LOU_GUIDE.md` 和 `YI_FRONTEND_API_EXAMPLE_ZH.md` 覆盖，已从 `docs/` 删除，避免继续引用旧前端状态。
