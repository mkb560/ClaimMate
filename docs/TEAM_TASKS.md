# 当前任务拆分

这份文档记录的是当前 ClaimMate 原型阶段的无 PR 任务拆分。它基于 `plan.md` 的当前阶段目标，以及 `AGENTS.md` 里记录的团队分工整理而成。

每个人都在自己的短分支上工作，先 push 做备份和同步，再在本地完成检查后合回 `main`。

## 日常协作规则

1. 一切都从最新的 `main` 开始
2. 只在自己的个人分支上开发
3. 每天至少 push 一次自己的分支
4. 改共享契约前先在群里说一声
5. 合回 `main` 之前先跑本地检查

## 当前任务分工

| 负责人 | 分支 | 主目标 | 具体交付物 | 注意事项 |
|---|---|---|---|---|
| Mingtao | `mingtao/ai-demo-polish` | 收紧 AI demo 质量，并先定第二主线技术契约 | 稳定本地 RAG、保证 KB-A + KB-B 可复现索引、改进 policy fact extraction、提供 demo 脚本、明确环境/模型选择、定义事故 workflow contract | 改共享 API 契约前先和 Ke 对齐 |
| Ke Wu | `ke/backend-integration` | 把 AI scaffold 接进可用的应用层 | 接 FastAPI 启动、整理 upload / ask app-layer route、定义最小 `cases` 和事故表单数据流、把第二主线接到 API / 存储 / 报告生成入口 | 除非对齐过共享契约，否则尽量不要改 AI internals |
| Yi-Hsien Lou | `lou/demo-ui` | 做出可演示的产品壳子 | 事故表单、policy upload 页面、简单 case dashboard、AI Q&A / chat 展示、事故报告预览、从 upload 到 answer 的干净 demo 流程 | 需要 Ke 的接口、也需要 Mingtao 的 schema 和示例 payload |

## 推荐推进顺序

下面这个顺序和当前 `plan.md` 的方向保持一致：

- Mingtao 继续专注 AI core 质量、RAG、dispute、deadline、chat behavior，以及第二主线共享契约
- Ke 继续围绕现有 AI scaffold 做 app-layer integration
- Lou 继续把最小可演示产品壳子搭出来
- Phase 1 先避免把精力投入在 auth、Stripe、完整生产级部署这类超范围内容上

### Phase 1：先把 demo 主路径补完整

- Mingtao：锁定真实 policy 上的问题质量，并把事故流程 schema / report payload 先定下来
- Ke：保住 upload / ask 可用，同时开始接事故 intake / report 的后端接口
- Lou：先做一条 happy-path 的 upload + ask 页面，再接 Stage A / Stage B 事故表单

### Phase 2：让完整故事更像一个产品

- Mingtao：保持 dispute detection、stage prompts、事故报告中间层稳定
- Ke：接 message persistence、`@AI` trigger、事故报告和 chat room 的连接
- Lou：做 chat timeline UI、stage-specific entry points、事故报告预览和 citation 展示

### Phase 3：把最终展示打磨顺

- Mingtao：准备固定 demo 问题、答案参考、备用路径
- Ke：补 seeded demo data、启动说明、最小 case lifecycle
- Lou：打磨 UX copy、截图、演示路径和页面转场

## 高协调文件

- `backend/main.py`
- `backend/models/ai_types.py`
- `backend/models/accident_types.py`
- `backend/.env.example`
- 数据库 schema 或 migration 文件
- 后端和前端共享的 request/response schema
