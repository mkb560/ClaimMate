# 协作说明

这个仓库当前使用的是一个比较轻量的 `branch-and-sync` 协作方式，不走 PR 审批流，但依然要保持基本的同步纪律和人工 review。

## 分支命名

每个人都应该使用短生命周期的个人分支，方便看出这项任务是谁在负责：

- `mingtao/<task>`
- `ke/<task>`
- `lou/<task>`

示例：

- `mingtao/rag-policy-extraction`
- `ke/chat-room-api`
- `lou/intake-form-ui`

## 团队边界

- Mingtao Ding：`backend/ai/`、RAG、embeddings、AI 契约、policy/dispute/deadline 逻辑
- Ke Wu：FastAPI integration、共享 DB/app layer、deployment、chat backend、后续 app 产品层
- Yi-Hsien Lou：前端 UI、事故表单流程、PDF/report UX、设计与展示交付

## 推荐工作流

1. 先同步本地 `main`
2. 从 `main` 拉一条只做单一任务的分支
3. 编写代码并运行相关本地检查
4. 把分支 push 到 GitHub，方便团队查看和备份
5. 如果要改高协调文件，先在群里发一句说明
6. 任务完成后，再同步最新 `main`、本地 merge、重新跑检查，然后再 push `main`

示例命令：

```bash
git checkout main
git pull origin main
git checkout -b mingtao/rag-query-routing
git push -u origin mingtao/rag-query-routing

git checkout main
git pull origin main
git merge mingtao/rag-query-routing
git push origin main
```

## 本地检查

后端相关改动至少要运行：

```bash
cd backend
./.venv/bin/pytest
```

如果本地还没有虚拟环境：

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pytest
```

GitHub Actions 当前会在每次 push 时运行后端测试，包括任务分支和 `main`。

## Push 前的基本要求

- 一个分支只聚焦一类任务
- 说明改了什么、为什么改、怎么验证的
- 如果改动了共享契约，要明确告诉队友
- 行为变化时要同步补测试
- 新增能力或新环境变量时，要同步更新 `AGENTS.md` 和 `backend/.env.example`
- 不要把过期的本地分支直接 merge 进 `main`；先 pull 最新 `main` 再解决冲突

## 高协调文件

下面这些文件如果要并行修改，最好先在群里对齐：

- `backend/main.py`
- `backend/models/ai_types.py`
- `backend/models/accident_types.py`
- `backend/.env.example`
- 共享数据库 schema / migration 文件
- 同时被 AI 模块和产品路由使用的 app-layer contract

## 轻量 review 建议

即使现在不用 PR，也建议在 push 共享改动到 `main` 前做一下轻量人工 review：

- AI/core 逻辑改动：重点看 grounding、citation、回归风险
- API 改动：重点看 contract 是否稳定、是否会影响联调
- UI 改动：尽量附截图，或者至少发一段简短说明

## GitHub 设置建议

这些设置仍然建议在 GitHub 仓库网页里手动保持：

- 如果团队明确采用 direct-sync 协作，就不要强制 PR
- 不允许对 `main` 强制 push
- 保留 `Backend CI` 可见，方便大家确认分支 push 后测试仍然通过
