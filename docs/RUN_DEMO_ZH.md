# 本地 Demo 运行说明

这份文档用于让团队成员在本地快速跑起 ClaimMate demo，不需要自己从头猜数据库、环境变量和调用顺序。

## 你需要准备什么

至少需要：

- Python 3.11+
- Docker Desktop
- 一个可用的 OpenAI API key

## 1. 启动本地 pgvector

如果本机还没有容器，可以先拉镜像并启动：

```bash
docker pull --platform linux/arm64 pgvector/pgvector:pg16
docker run -d --platform linux/arm64 \
  --name claimmate-pgvector \
  -e POSTGRES_USER=claimmate \
  -e POSTGRES_PASSWORD=claimmate \
  -e POSTGRES_DB=claimmate \
  -p 5433:5432 \
  pgvector/pgvector:pg16
```

如果你的机器不是 Apple Silicon，可以去掉 `--platform linux/arm64`。

确认容器在跑：

```bash
docker ps --filter name=claimmate-pgvector
```

## 2. 安装后端依赖

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install -e '.[dev]'
```

## 3. 配置环境变量

可以手动导出，也可以照着 `backend/.env.example` 建一个 `.env`。

最小需要：

```bash
export OPENAI_API_KEY="your_key"
export DATABASE_URL="postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
```

如果前端和后端分开端口跑，默认本地已允许这些前端来源：

```text
http://localhost:3000
http://127.0.0.1:3000
http://localhost:5173
http://127.0.0.1:5173
```

如果你要自定义，可以加：

```bash
export CORS_ALLOW_ORIGINS="http://localhost:3000,http://localhost:5173"
```

## 4. 启动后端

```bash
cd backend
./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

正常会返回类似：

```json
{
  "status": "ok",
  "ai_ready": true,
  "ai_bootstrap_error": null
}
```

## 5. 先用固定 demo policy，或手动上传 PDF

仓库里自带的 3 份 demo policy PDF 放在：

```text
demo_policy_pdfs/
```

如果你只是想快速演示，最省事的是直接调用内建 seed route：

```bash
curl -X POST "http://127.0.0.1:8000/cases/allstate-change-2025-05/demo/seed-policy"
```

如果你想把某一份固定 demo PDF 种到自定义 `case_id`，可以显式传 `policy_key`：

```bash
curl -X POST "http://127.0.0.1:8000/cases/demo-policy-case/demo/seed-policy" \
  -H "Content-Type: application/json" \
  -d '{"policy_key":"progressive-verification"}'
```

也可以本地直接跑脚本：

```bash
cd backend
./.venv/bin/python scripts/seed_demo_policy.py --case-id allstate-change-2025-05
```

如果你想手动上传真实文件，也可以继续这样做：

```bash
curl -X POST "http://127.0.0.1:8000/cases/demo-case/policy" \
  -F "file=@/absolute/path/to/policy.pdf"
```

成功返回示例：

```json
{
  "case_id": "demo-case",
  "filename": "policy.pdf",
  "chunk_count": 10,
  "status": "indexed"
}
```

## 6. 问一个问题

```bash
curl -X POST "http://127.0.0.1:8000/cases/allstate-change-2025-05/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Who are the policyholders and what is the policy number?"}'
```

成功返回示例：

```json
{
  "case_id": "demo-case",
  "question": "Who are the policyholders and what is the policy number?",
  "answer": "The policyholders listed in the document are ...",
  "disclaimer": "This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
  "citations": [...]
}
```

## 7. 跑固定 demo 评测

如果你想确认当前 demo 还是稳定的，可以直接跑：

```bash
cd backend
./.venv/bin/python scripts/run_demo_eval.py --json-out /tmp/claimmate_demo_eval.json
```

如果看到：

```text
Summary: 9/9 passed
```

说明现在这套固定 demo 题集还是通的。

## 8. 当前推荐 demo 题

最稳的题集和讲解顺序已经整理在：

- `docs/DEMO_PLAYBOOK_ZH.md`

## 9. 前端接法

Lou 的前端接口示例在：

- `docs/YI_FRONTEND_API_EXAMPLE_ZH.md`

Ke 的接口契约在：

- `docs/KE_API_CONTRACT_ZH.md`

## 10. 当前最常见问题

### `ai_ready` 是 `false`

通常是：

- `OPENAI_API_KEY` 没配
- `DATABASE_URL` 没配
- pgvector 容器没起来

### 上传时报 `Only PDF uploads are supported`

说明上传的文件不是 PDF，或者浏览器传来的文件类型不对。

### 前端报跨域

说明你的前端来源不在 `CORS_ALLOW_ORIGINS` 里。把对应端口加进去，然后重启后端。

### 提问没结果或结果不对

先确认：

1. 该 `case_id` 之前已经成功上传过 policy
2. OpenAI key 可用
3. 数据库连接正常
4. 你问的是当前 demo 文档里真实能答的问题
5. 如果你走的是固定 demo case，先确认已经调用过 `/cases/{case_id}/demo/seed-policy`

## 11. 远程共享给队友

如果 Ke 和 Lou 不在同一地点，不打算各自本地起 RAG，而是直接连你这台机器已经跑好的后端，请看：

- `docs/REMOTE_SHARED_BACKEND_ZH.md`
