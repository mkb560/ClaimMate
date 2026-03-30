# 远程共享后端说明

这份文档对应你们的协作情况 1：

- 只有 Mingtao 这台机器跑后端
- 只有 Mingtao 这台机器持有 `pgvector`、本地 PDF、OpenAI key
- Ke 和 Lou 不需要自己本地重建 RAG
- Ke 和 Lou 直接调用你暴露出来的公网 API

这适合你们住得很远、但希望前后端继续并行开发的场景。

## 当前共享架构

数据和能力都留在 Mingtao 的电脑上：

- 本地 PostgreSQL + `pgvector`
- 本地上传的 policy PDF
- 本地 KB-B 向量库
- 本地 OpenAI API 调用

对外暴露的只有 FastAPI：

- 你本机后端跑在 `http://127.0.0.1:8000`
- `ngrok` 把它映射成一个临时公网 URL
- 另外两位同学只需要拿这个公网 URL 调接口

## 同学需要自己准备什么

如果他们只是连你的后端，不需要以下东西：

- 不需要本地 `pgvector`
- 不需要本地重新 ingest PDF
- 不需要本地 OpenAI API key
- 不需要本地重新跑 RAG

他们真正需要的只有：

- 你的公网 API base URL
- 约定好的 `case_id`
- 当前 demo 要问的问题

## 你这边怎么启动共享后端

先确认：

- Docker 里的 `claimmate-pgvector` 正在运行
- 你的 `OPENAI_API_KEY` 可用
- 你的 `DATABASE_URL` 指向本地 pgvector
- 机器不要睡眠，不要断网

然后运行：

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
./scripts/run_shared_backend.sh
```

如果你的 Python 不在 `backend/.venv/bin/python`，可以显式指定：

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
export PYTHON_BIN="/absolute/path/to/python"
./scripts/run_shared_backend.sh
```

如果 `uvicorn` 不在同一个 Python 环境里，也可以单独指定：

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
export PYTHON_BIN="/absolute/path/to/python"
export UVICORN_BIN="/absolute/path/to/uvicorn"
./scripts/run_shared_backend.sh
```

正常启动后，终端会打印一个类似下面的公网地址：

```text
Public API base URL:
  https://abc123.ngrok-free.app
```

把这个 URL 发给 Ke 和 Lou 就可以。

## Ke 和 Lou 怎么用

他们拿到的是一个 base URL，比如：

```text
https://abc123.ngrok-free.app
```

那他们可以直接调用：

```text
GET  https://abc123.ngrok-free.app/health
POST https://abc123.ngrok-free.app/cases/demo-case/policy
POST https://abc123.ngrok-free.app/cases/demo-case/ask
```

前端只要把 API base URL 改成你的 ngrok 地址即可。

如果 Lou 本地前端在 `http://localhost:3000` 或 `http://localhost:5173`，当前后端默认已经允许跨域。

## 可直接转发给 Ke 和 Lou 的消息模板

下面这段你可以直接复制给他们。每次只需要把 `<当前 ngrok URL>` 替换成你这次启动后端后拿到的最新地址。

当前这次共享会话里，已经验证可用的地址是：

```text
https://exasperatingly-unprologued-elease.ngrok-free.dev
```

这个地址在 **2026-03-30** 已经通过：

```text
GET https://exasperatingly-unprologued-elease.ngrok-free.dev/health
```

返回：

```json
{"status":"ok","ai_ready":true,"ai_bootstrap_error":null}
```

```text
大家现在可以直接连我这边已经跑好的 ClaimMate 后端，不需要你们自己本地起 RAG、pgvector 或 OpenAI。

当前公网 API base URL：
<当前 ngrok URL>

可用接口：
- GET /health
- POST /cases/{case_id}/policy
- POST /cases/{case_id}/ask

完整地址：
- <当前 ngrok URL>/health
- <当前 ngrok URL>/cases/{case_id}/policy
- <当前 ngrok URL>/cases/{case_id}/ask

你们现在不需要自己做这些事：
- 不需要本地起 pgvector
- 不需要本地重新 ingest PDF
- 不需要本地 OpenAI API key
- 不需要本地重跑 RAG

你们只要直接调我这个 API 就行。现在数据和模型都跑在我电脑上。

调用方式：

1. 健康检查
curl <当前 ngrok URL>/health

2. 上传 policy PDF
curl -X POST "<当前 ngrok URL>/cases/demo-case/policy" \
  -F "file=@/absolute/path/to/policy.pdf"

3. 提问
curl -X POST "<当前 ngrok URL>/cases/demo-case/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Who are the policyholders and what is the policy number?"}'

建议：
- Ke 先按这个 base URL 接后端接口
- Lou 先把前端 API base URL 指到这个地址，直接做 upload + ask 的 happy path

注意：
- 这个地址是临时共享地址，如果我重启服务或 tunnel，URL 可能会变
- 如果你们调接口时报错，先把报错原文发我

文档也已经在仓库里：
- docs/REMOTE_SHARED_BACKEND_ZH.md
- docs/KE_API_CONTRACT_ZH.md
- docs/YI_FRONTEND_API_EXAMPLE_ZH.md
```

## 最小联调流程

推荐你们这样协作：

1. 你启动共享后端并拿到 ngrok URL
2. 你先自己访问 `GET /health`，确认 `ai_ready=true`
3. 你把 base URL 发给 Ke 和 Lou
4. Ke 用这个 URL 接后端接口
5. Lou 用这个 URL 接前端上传和提问页面
6. 你负责维护 PDF、case_id、RAG 数据和回答质量

## 一个重要约束

现在上传上来的 policy PDF 和向量数据，都会写到你本机：

- PDF 保存在 `backend/.local_data/policies/`
- 向量写入你本机的 `pgvector`

这意味着：

- 他们上传的文件，本质上是传到你电脑
- 他们问的问题，也是由你电脑上的数据库和 OpenAI key 处理

所以这个模式适合：

- 课程项目联调
- demo 演示
- 短期协作

它不适合长期正式部署。

## 常见问题

### 1. 为什么同学不需要自己本地起 RAG

因为 RAG 真正依赖的是：

- 你的 PDF
- 你的向量库
- 你的 OpenAI key
- 你的 FastAPI

他们如果只是调用你的 API，就等于直接使用这套已经跑好的服务。

### 2. 为什么每次 URL 都可能变

`ngrok` 的免费临时地址通常不是固定的。你重启 tunnel 之后，URL 可能变化，所以每次新开共享会话，都要把最新地址发给同学。

### 3. 这样安全吗

它比直接开家里路由器端口安全得多，但仍然要注意：

- 只把 URL 发给你信任的同学
- 不共享超过需要的时长
- 不把真实敏感个人数据长期留在 demo 环境里
- 不把 OpenAI key 写进仓库

### 4. 如果他们前端还是报跨域

当前后端默认允许本地开发来源：

- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

并且还允许任意 `localhost` / `127.0.0.1` 端口的本地开发来源。

如果他们不是本地端口，而是别的预览域名，再把那个来源加到：

```text
CORS_ALLOW_ORIGINS
```

里并重启后端。
