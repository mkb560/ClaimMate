# 事故与 Chat Demo 资产

这份文档给 Lou / 前端 / demo 使用，目标是提供一套固定、可重复、字段不靠猜的第二主线样例。

## 这份资产解决什么问题

现在事故工作流和 chat event API 已经接进后端了，但如果前端每次都自己手写 payload，会很容易出现：

- 字段名和后端 schema 对不上
- claim dates 设得不对，deadline demo 不触发
- stage 1 / stage 3 的 chat event 参与者组合不一致
- report payload 和 chat context 每次长得不一样，不利于 UI 对齐

所以现在新增了一条固定种子脚本：

- [seed_accident_demo.py](/Users/dingmingtao/Desktop/USC/研二下/DSCI560/ClaimMate/backend/scripts/seed_accident_demo.py)

以及一份共享 demo data source：

- [demo_seed_data.py](/Users/dingmingtao/Desktop/USC/研二下/DSCI560/ClaimMate/backend/app/demo_seed_data.py)

## 固定 demo case

- `case_id`: `demo-accident-2026-04`

这条 case 会被写入：

- Stage A 现场收集样例
- Stage B 回家补充样例
- claim dates
- 生成后的 accident report payload
- 生成后的 accident chat context
- 3 份 chat event request
- 能成功生成的 chat response 样例

## 运行方式

```bash
cd backend
DATABASE_URL="postgresql+psycopg://claimmate:claimmate@127.0.0.1:5433/claimmate" \
./.venv/bin/python scripts/seed_accident_demo.py
```

默认输出目录：

```text
backend/.local_data/demo_cases/demo-accident-2026-04/
```

如果本地 KB-B 还没建好，脚本会尝试自动把仓库根目录 `claimmate_rag_docs/` 建成 KB-B。

说明：

- `deadline_stage_1` chat response 不依赖 OpenAI，只依赖 claim dates 和 `cases` 表
- `claim_rule_stage_1` / `claim_rule_stage_3` 这两条 chat response 依赖 KB-B 已经可用
- KB-B 一旦已经建好，这两条 claim-rule response 现在会优先走 deterministic regulatory extraction

## 会生成哪些文件

关键文件包括：

- `request_stage_a.json`
- `request_stage_b.json`
- `request_claim_dates.json`
- `response_report.json`
- `request_chat_deadline_stage_1.json`
- `response_chat_deadline_stage_1.json`
- `request_chat_claim_rule_stage_1.json`
- `response_chat_claim_rule_stage_1.json`
- `request_chat_claim_rule_stage_3.json`
- `response_chat_claim_rule_stage_3.json`
- `summary.json`

## 前端最适合先接的顺序

推荐直接按这个顺序做：

1. `POST /cases` 或直接使用固定 `case_id`
2. `PATCH /cases/{case_id}/accident/stage-a`
3. `PATCH /cases/{case_id}/accident/stage-b`
4. `PATCH /cases/{case_id}/claim-dates`
5. `POST /cases/{case_id}/accident/report`
6. `GET /cases/{case_id}/accident/report`
7. `POST /cases/{case_id}/chat/event`

## 这套 demo 最适合展示什么

- Stage A 表单如何收集事故现场核心证据
- Stage B 表单如何补充 witness / police / repair 信息
- report preview 如何显示标准化 summary / timeline / comparison rows
- stage 1 chat 如何给出 deadline reminder
- stage 3 chat 如何用更中立口吻回答法规问题

## 说明

- 这些文件是 demo 资产，不是生产真实用户数据
- 如果你想刷新生成内容，直接重新跑脚本即可
- 如果之后 schema 有变化，优先改 [demo_seed_data.py](/Users/dingmingtao/Desktop/USC/研二下/DSCI560/ClaimMate/backend/app/demo_seed_data.py)，不要只改文档里的静态示例
