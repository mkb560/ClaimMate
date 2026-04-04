# 给 Lou 的开发说明

这份说明是给你当前阶段直接开工用的，目标不是一次做完整产品，而是先把 demo 展示路径做出来。

## 你现在接手的项目状态

当前仓库里，AI 核心已经能工作，但前端产品层基本还没做。

- AI 侧已经支持：
  - policy PDF ingest
  - KB-B regulatory retrieval
  - policy Q&A
  - dispute detection
  - deadline reminder logic
  - chat AI scaffold
- 后端产品入口现在已经有最小 demo API：
  - `GET /health`
  - `GET /demo/policies`
  - `GET /cases/{case_id}/policy`
  - `POST /cases/{case_id}/demo/seed-policy`
  - `POST /cases/{case_id}/policy`
  - `POST /cases/{case_id}/ask`
- 第二主线的共享 schema 也已经先定好了：
  - `backend/models/accident_types.py`
  - `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md`
- 也就是说：
  - AI 能力是有的
  - 但是用户还没有一个顺手的界面去体验这些能力

所以你当前最重要的任务，是把“好 demo”做出来。

## 你负责什么

你主要负责三类东西：

1. 用户看到和操作到的界面
2. demo 流程的顺滑度
3. 最终展示时的观感和叙事感

第一阶段建议你重点做：

- accident intake form
- policy upload 页面
- case 页面 / dashboard
- AI 问答或 chat 展示区

## 你第一阶段最该做的 4 件事

### 1. 先把第二主线的 Stage A / Stage B 做成可用前端流程

这部分现在最值得你先动，因为 schema 已经先定好了，不需要你自己重新发明字段。

你要先看的文件：

- `backend/models/accident_types.py`
- `docs/ACCIDENT_WORKFLOW_CONTRACT_ZH.md`

你前端最适合先做的是：

- Stage A：现场快速收集
- Stage B：回家后补充
- 事故照片 checklist
- 事故报告预览壳子

### 2. 先做 happy path，不要一开始做全量系统

先只做这条 demo 路：

1. 用户进入页面
2. 上传 policy PDF
3. 输入一个问题
4. 看到 AI 回答和 citations

只要这条链路顺了，整个项目就已经能 demo。

但如果你们想更贴近 proposal 里的完整故事，建议同时并行做这条第二主线：

1. 用户进入事故表单
2. 先完成 Stage A
3. 再补 Stage B
4. 预览标准化事故报告

### 3. 先做页面壳子，就算后端接口还没全好也可以先动

如果 Ke 的接口还没完全 ready，你也可以先用 mock data 做页面。

建议先准备这些页面：

- 上传页
- case 详情页
- AI 问答面板
- 如果时间够，再做 chat timeline

你不用等所有 API 都做好才开始。

### 4. UI 上要突出“保险理赔助手”的感觉

当前最值得展示的不是复杂动效，而是“这个产品真的能帮用户理解保单和理赔时限”。

建议页面重点突出：

- 我上传了什么 policy
- 当前问了什么问题
- AI 给了什么回答
- 引用了什么来源
- 接下来建议用户做什么

比起很炫的界面，更重要的是让老师一眼看懂：
这个工具能帮助普通用户处理车险 claim。

### 5. 如果 chat 来不及，就先把问答体验和事故表单体验做扎实

现阶段 chat 不是唯一必须项。

如果时间有限，优先级建议是：

1. Stage A / Stage B 表单
2. upload + ask
3. answer + citations 展示
4. case summary / report preview
5. chat UI

## 你现在先不要花太多时间做的事

当前阶段不建议优先投入：

- 很复杂的设计系统
- 很重的动画
- 多角色权限体系
- 很完整的 account/profile 流程
- 细碎但不影响 demo 的视觉打磨

现在更重要的是：
让一个第一次看你们项目的人，3 分钟内完成上传并看到有说服力的 AI 结果。

## 你和 Ke / Mingtao 的协作边界

默认边界是：

- Mingtao 负责 AI 结果本身和回答质量
- Ke 负责 API 和后端接线
- 你负责用户体验和展示路径

你最需要对齐的东西有两个：

### 和 Ke 对齐

- upload endpoint 长什么样
- ask endpoint 长什么样
- request / response JSON 怎么定义
- case 页面需要哪些字段
- Stage A / Stage B 的接口怎么定义
- report preview / report download 怎么接

### 和 Mingtao 对齐

- demo 时最适合展示的 3 到 5 个问题
- citation 怎么展示更清楚
- 哪些回答适合做“推荐问题”
- 事故表单字段不要偏离 `accident_types.py`
- 事故报告预览优先围绕 `AccidentReportPayload`

## 你当前推荐分支

建议直接用：

```bash
git checkout main
git pull origin main
git checkout -b lou/demo-ui
git push -u origin lou/demo-ui
```

## 现在的协作规则

这个仓库当前不用 PR，走 branch-and-sync：

1. 从最新 `main` 开分支
2. 在你自己的分支开发
3. 每天至少 push 一次
4. 如果你要改共享接口或高协调文件，先在群里说
5. 合回 `main` 前先同步最新 `main`
6. 如果有页面变化，最好发截图给大家快速确认

## 你完成后应该交付什么

当前阶段，希望你交出来的是：

- 一个清楚的 Stage A / Stage B 事故表单流程
- 一个干净可演示的 upload 页面
- 一个 case 页面或问答页面
- 一个清楚展示 AI answer + citation 的组件
- 一个事故报告预览壳子
- 如果来得及，再补一个简版 chat 界面

如果你先把这些做出来，proposal 里的第二主线就会真正有产品形态，不再只是概念图。
