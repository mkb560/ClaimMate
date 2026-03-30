# 第二主线技术契约

这份文档只定义第二主线里 Mingtao 负责先定下来的技术骨架，不等于完整产品已经做完。

目标是把下面这条链路的共享数据契约先固定住：

```text
Stage A 现场快速收集
-> Stage B 回家补充
-> 标准化事故报告 payload
-> PDF generator
-> group chat pinned context
```

## 你现在已经落地的文件

- 共享 schema:
  - `backend/models/accident_types.py`
- 确定性 payload builder:
  - `backend/ai/accident/report_payload_builder.py`
- 测试:
  - `backend/tests/test_accident_payload_builder.py`

这些文件的目标不是直接替代前端或 PDF，而是先把事故数据长什么样、最终报告长什么样、后面 chat 要消费什么先定清楚。

## Mingtao 在第二主线里的边界

Mingtao 负责：

- 定义 Stage A / Stage B 共享字段
- 定义标准化事故报告 payload
- 定义给 chat / pinned PDF 用的上下文结构
- 提供确定性的整理逻辑和测试样例

Mingtao 目前不需要优先负责：

- 完整事故表单前端实现
- 最终 PDF 排版 UI
- 文件上传页面
- WebSocket 聊天产品层

## Stage A 契约

`StageAAccidentIntake`

用途：现场 5 分钟内快速收集最关键证据。

当前字段包括：

- `occurred_at`
- `location`
- `owner_party`
- `other_party`
- `injuries_reported`
- `police_called`
- `drivable`
- `tow_requested`
- `quick_summary`
- `photo_attachments`
- `stage_completed_at`

设计原则：

- 尽量只收事故发生当下必须抓住的信息
- 允许大量字段为空，避免现场流程太重
- 所有后续报告生成都允许在 Stage B 再补完

## Stage B 契约

`StageBAccidentIntake`

用途：用户回家后补全更详细的 claim follow-up 信息。

当前字段包括：

- `detailed_narrative`
- `damage_summary`
- `weather_conditions`
- `road_conditions`
- `witness_contacts`
- `police_report_number`
- `adjuster_name`
- `repair_shop_name`
- `follow_up_notes`
- `additional_photos`
- `stage_completed_at`

设计原则：

- 支持补充详细叙述，而不是要求现场一次填完
- 支持 witness / police / adjuster / repair shop 这些后续沟通信息
- 支持补充照片而不覆盖 Stage A 现场照片

## 标准化事故报告 payload

`AccidentReportPayload`

这个结构是给后续 PDF generator 和 case summary 层消费的统一中间格式。

当前包含：

- 核心摘要：`accident_summary`
- 基本事实：`occurrence_time`、`location_summary`
- 双方主体：`owner_party`、`other_party`
- 条件状态：`injuries_reported`、`police_called`、`drivable`、`tow_requested`
- 详细补充：`detailed_narrative`、`damage_summary`
- 后续关联：`witness_contacts`、`police_report_number`、`adjuster_name`、`repair_shop_name`
- 展示支撑：`photo_attachments`、`party_comparison_rows`、`timeline_entries`
- 缺失提醒：`missing_items`

## 给 chat / pinned PDF 的共享上下文

`AccidentChatContext`

这个结构是给第三主线使用的。

当前包含：

- `pinned_document_title`
- `summary`
- `key_facts`
- `party_comparison_rows`
- `follow_up_items`
- `generated_at`

预期用法：

- 创建 group chat 时，把生成好的事故报告作为 pinned document
- 同时把 `AccidentChatContext` 写进 chat room 的初始上下文
- 这样 adjuster / repair shop 一进来就能看到统一事故材料，而不是让车主反复重复

## Ke 要接什么

Ke 主要基于这些契约去做产品层：

- `POST /cases`
- `PATCH /cases/{case_id}/accident/stage-a`
- `PATCH /cases/{case_id}/accident/stage-b`
- `POST /cases/{case_id}/accident/report`
- `GET /cases/{case_id}/accident/report`

以及：

- 把事故数据存到数据库
- 调用 builder 生成标准化 payload
- 再把 payload 交给 PDF generator 和后续 chat room

## Lou 要接什么

Lou 主要基于这些契约去做前端体验：

- Stage A 现场快速表单
- Stage B 回家补充表单
- 照片 checklist 和补充照片入口
- 事故报告预览

重点是：

- 前端字段名直接对齐 schema
- 不要先自由发挥出另一套结构

## 现在还没做的

这批契约代码目前还没有接进真实 API，也还没有接进 PDF generator。

也就是说，现在已经做的是：

- 共享数据结构
- 事故报告中间层
- chat 上下文 contract

还没做的是：

- 真正的 FastAPI 路由
- 数据库存储
- PDF 文件生成
- 和 group chat room 的真正联动
