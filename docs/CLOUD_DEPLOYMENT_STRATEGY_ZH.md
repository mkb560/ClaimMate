# ClaimMate 三人上云策略

这份文档的目标不是替代未来正式的部署文档，而是给当前三人小组一个清晰、现实、可以执行的上云路线。

它主要回答 4 个问题：

1. 现在要不要上云
2. 哪些东西现在已经可以上云
3. 哪些东西必须先改代码再上云
4. Mingtao / Ke / Lou 三个人各自负责什么

## 先说结论

建议采用下面这条路线：

- 现在开始准备并落一个 **staging 云环境**
- 不建议一开始就把所有东西做成正式 production
- 也不建议拖到最后一天才第一次上云

更具体地说：

- `FastAPI backend`：现在就可以开始准备上云
- `PostgreSQL + pgvector`：应该和第一次真实云端 backend 一起上
- `文件存储`：只要你们要在云上真实上传 PDF / 图片，就应该同时改成对象存储
- `前端正式上线`：可以稍晚一点，等 Lou 的页面稳定后再上

## 推荐的目标架构

### 推荐组合

- 前端：Vercel
- 后端：Railway
- 数据库：Supabase Postgres + `pgvector`
- 文件存储：AWS S3 或 S3-compatible bucket

### 为什么这样搭配

- 当前后端就是标准 FastAPI，放 Railway 很顺
- 当前 AI 核心依赖 Postgres + `pgvector`，适合直接用托管 Postgres
- policy PDF、事故图片、后续报告文件都不适合继续放在服务本地磁盘
- 如果 Lou 后面是 Next.js，Vercel 会比自托管省很多事

## 为什么不要继续靠 ngrok

当前这套方式是：

- 你本地电脑跑 FastAPI
- 你本地电脑跑 `pgvector`
- 用 `ngrok` 暴露临时公网地址

它只适合：

- 课程项目联调
- 快速 demo
- 临时远程开发

它不适合长期环境，因为：

- 电脑重启、睡眠、断网就会断
- 免费公网地址会变
- 文件和数据库都绑在个人机器上
- 队友依赖你电脑在线

## 你们现在已经可以上云的部分

### 1. FastAPI backend

当前 [main.py](/Users/dingmingtao/Desktop/USC/研二下/DSCI560/ClaimMate/backend/main.py) 已经有：

- `GET /health`
- `POST /cases/{case_id}/policy`
- `POST /cases/{case_id}/ask`

所以从“服务能启动并对外提供 API”这个角度，它已经具备 staging 部署基础。

### 2. AI 核心

这些模块现在已经是可部署状态：

- RAG 检索与回答
- embeddings
- policy ingest
- KB-B indexing
- citation formatting
- dispute detection
- deadline logic

只要数据库和环境变量对上，就可以放到云端服务里运行。

### 3. 托管数据库

你们现在已经明确依赖：

- PostgreSQL
- `pgvector`

所以数据库完全可以现在就上云，而不是继续长期依赖本地 Docker。

### 4. KB-B 向量库

一旦数据库上云，KB-B 也可以直接重新索引到云端数据库。

也就是说：

- 本地 `claimmate_rag_docs/` 可以继续保留
- 最终向量可以写到云上的 Postgres + `pgvector`

## 现在还不适合直接上云的部分

### 1. 本地文件存储

当前上传 policy 的逻辑会把文件写到：

- `backend/.local_data/policies/`

这在本地 demo 时没问题，但上云后不应该继续依赖这种本地路径。

原因：

- 云服务实例的本地文件通常不是长期持久化存储
- 服务重启 / 重新部署后，本地文件可能丢失
- 多实例时更无法保证一致性

所以只要你们要在云上认真跑上传流程，就应该把 policy PDF / 事故图片改成对象存储。

### 2. 第二主线的真实文件流

第二主线当前已经有 schema 和 report payload builder，但还没有真正做：

- 事故照片上传到云对象存储
- 报告文件输出到稳定存储
- 前后端完整接线

所以第二主线的“产品体验”还没到正式上云阶段，但它的共享契约已经可以指导后续上云设计。

### 3. 群聊产品层

第三主线当前有 AI scaffold，但还没有完整的：

- chat room
- WebSocket
- invite link
- pinned report

所以这部分现在不应该成为第一次上云的阻塞点。

## 推荐的时间顺序

### 第一步：先做一个稳定的 staging backend

目标：

- backend 不再依赖 `ngrok`
- 队友可以用固定 staging URL 联调
- 数据库放到云端

这一阶段建议就做：

- Railway 上线 FastAPI
- Supabase 上线 Postgres + `pgvector`
- 先保证 `/health`、`/policy`、`/ask` 跑通

### 第二步：把文件存储云化

一旦你们要在 staging 上真实上传 policy / 图片，就要补：

- S3 bucket 或 S3-compatible bucket
- 上传后的对象路径管理
- 对应 metadata 持久化

### 第三步：前端上线

等 Lou 的页面稳定后：

- 再上 Vercel
- 前端通过环境变量区分本地 / staging / 未来 production API base URL

### 第四步：再考虑正式 production

等下面这些都稳定后再谈 production：

- 第二主线完整接线
- 群聊产品层成型
- 文件存储改完
- case schema 稳定
- demo 路径稳定

## 三个人的分工

### Mingtao 负责什么

Mingtao 负责的是“AI 和数据契约能不能被稳定搬上云”。

当前优先负责：

- 保证 AI 核心在云数据库下仍能工作
- 保证 KB-A / KB-B indexing 在云环境可重复
- 管理 AI 相关环境变量说明
- 保持第二主线共享 schema 稳定
- 定义 policy / accident report / chat 上下文的共享 contract

上云相关最适合 Mingtao 做的事：

- 把“本地文件路径依赖”抽象成“对象存储输入”契约
- 给 Ke 明确哪些 AI 函数该如何接入 app layer
- 准备一套 staging seed / demo 数据
- 保证云上 RAG 的回答质量和 citation 仍稳定

Mingtao 当前不必优先亲自做：

- Railway 项目配置
- 域名
- 前端部署

### Ke 负责什么

Ke 是三个人里最适合主导“backend 上云实施”的人。

Ke 当前优先负责：

- Railway 部署 FastAPI
- 配置服务环境变量
- 接正式 Postgres 连接
- 接对象存储
- 整理 `cases` / `documents` / 第二主线相关表结构
- 后续再处理 chat room、invite link、deployment polish

Ke 是上云主责任人，原因很简单：

- 上云主要落在 app layer
- API、存储、数据库、deployment 都在他负责范围里

### Lou 负责什么

Lou 主要负责“前端怎么适应 staging / production 环境”。

Lou 当前优先负责：

- 前端 API base URL 配置
- 本地 / staging 环境切换
- 上传、提问、事故表单、报告预览页面在 staging 上联调
- 为未来 Vercel 部署准备环境变量与页面行为

Lou 不需要现在自己主导数据库或后端部署，但她要尽早按 staging URL 开始联调。

## 你们现在立刻能做的上云版本

最推荐的“现在就能开始”的版本是：

### 现在就上

- Railway：FastAPI staging backend
- Supabase：Postgres + `pgvector`

### 等 backend 云化后马上补

- S3 / S3-compatible bucket：policy PDF 与事故图片

### 页面成熟后再上

- Vercel：前端

## 当前可以先不急着上云的部分

这些可以等后面更稳定再做：

- 正式 production 域名
- 多环境 CI/CD 流水线
- 完整监控 / tracing
- 压力测试
- Stripe / payment
- 完整 chat WebSocket 体系

## 一个务实的判断

如果你问“现在最值得先上云的是什么”，答案是：

1. `FastAPI + cloud Postgres`
2. 然后是 `对象存储`
3. 最后才是 `前端正式上线`

因为现在真正限制团队联调稳定性的，不是前端有没有上 Vercel，而是：

- backend 还绑在个人电脑上
- 数据库还绑在本地 Docker 上
- 上传文件还绑在本地磁盘上

## 推荐下一步

如果你们现在准备真的开始上云，我建议下一步顺序是：

1. Ke 先出一个 Railway staging backend
2. 同时把数据库接到云上的 Postgres + `pgvector`
3. Mingtao 协助确认 AI core、KB-B indexing、demo 问题在 staging 上仍然正常
4. 然后再把 policy / 图片文件改到对象存储
5. Lou 再把前端开始切到 staging API

## 参考方向

当前这个策略主要参考了这些官方方向：

- Railway 的 FastAPI 部署与 public networking
- Railway volume 的限制与使用边界
- Vercel 的 Next.js 部署方式
- Supabase 的 `pgvector` 扩展支持

这些平台能力会变化，所以真正动手前，最好再按当时的官方文档核一次。
