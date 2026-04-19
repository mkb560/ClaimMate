# Cloud Staging（Railway）说明

这份文档只面向 **私下云端验证**，不代表现在就要让队友从本机 ngrok 切到云端。

## 当前目标

把 ClaimMate 的 **AI backend** 做成一条可私测的云端 staging 路径，并把下面 4 件事一起搬上云：

1. policy 文件存储
2. KB-B 索引流程
3. smoke / eval
4. 日志监控

## 当前云端形态

- Railway project：`claimmate-staging`
- backend service：`claimmate-backend`
- 托管 Postgres：`Postgres`
- backend volume：挂载到 `/app/backend/.local_data`

当前公网地址：

- `https://claimmate-backend-production.up.railway.app`

## 1. policy 文件存储

当前 cloud staging 没有直接改成 S3，而是先采用：

- **单实例 backend**
- **Railway volume**
- 挂载到 backend 的 `.local_data`

这意味着：

- `POST /cases/{case_id}/policy`
- `POST /cases/{case_id}/demo/seed-policy`

在云端仍然可以工作，而且写入的是 Railway volume，而不是临时容器层。

这套方案适合当前课程项目和 staging 验证；如果后面真要长期运行，再考虑把 policy 文件迁到对象存储。

## 2. KB-B 索引流程

新增脚本：

- `backend/scripts/bootstrap_cloud_data.py`

用途：

- 对目标数据库执行 `bootstrap_vector_store(...)`
- 检查 KB-B 是否已存在
- 必要时把本地 `claimmate_rag_docs/` 索引进目标数据库
- 可选地通过远程 `seed-policy` 验证云端 policy volume 是否可写

本地对云数据库执行示例：

```bash
cd backend
DATABASE_URL=postgresql+psycopg://... \
./.venv/bin/python scripts/bootstrap_cloud_data.py \
  --base-url https://claimmate-backend-production.up.railway.app
```

## 3. smoke / eval

### 3.1 现有 demo smoke

已有：

- `backend/scripts/run_demo_smoke.py`

它适合验证：

- `/health`
- demo policy
- seed-policy
- ask
- seed-accident
- case snapshot
- `chat/messages`
- `chat/event`

打云端示例：

```bash
cd backend
./.venv/bin/python scripts/run_demo_smoke.py \
  --base-url https://claimmate-backend-production.up.railway.app
```

### 3.2 新增 collab smoke

新增：

- `backend/scripts/run_collab_smoke.py`

它适合验证 Milestone 3 / product-layer 路径：

- `register`
- `login` / `me`
- create case
- seed accident
- invite
- accept invite
- `chat/messages`
- `chat/messages` persistence
- `wss://.../ws/cases/{case_id}`

打云端示例：

```bash
cd backend
./.venv/bin/python scripts/run_collab_smoke.py \
  --base-url https://claimmate-backend-production.up.railway.app
```

### 3.3 deterministic eval

已有：

- `backend/scripts/run_chat_ai_eval.py`

这条仍然适合本地 deterministic regression，不直接依赖 Railway。

## 4. 日志监控

### 当前已补的观测能力

新增配置：

- `APP_LOG_LEVEL`
- `APP_LOG_JSON`

默认推荐：

- `APP_LOG_LEVEL=INFO`
- `APP_LOG_JSON=true`

新增能力：

- 启动日志
- AI bootstrap success / failure 日志
- 每个 HTTP 请求的结构化日志
- `X-Request-ID` 响应头
- health response 里返回：
  - `auth_mode`
  - `policy_storage_ready`
  - `policy_storage_error`

### Railway 上建议重点看

重点关注日志里的：

- `application_startup`
- `ai_bootstrap_succeeded`
- `ai_bootstrap_failed`
- `http_request_completed`
- `http_request_failed`

## 推荐私测顺序

在你准备切同学到云端之前，建议至少按这个顺序再跑一遍：

1. `GET /health`
2. `bootstrap_cloud_data.py`
3. `run_demo_smoke.py --base-url ...`
4. `run_collab_smoke.py --base-url ...`
5. 再让本地 frontend 临时连 Railway backend 做一次浏览器侧联调

## 当前建议

在你确认：

- data bootstrap 正常
- demo smoke 正常
- collab smoke 正常
- Railway logs 没有明显异常

之前，**不要让队友切到云端**。先继续使用你本机的共享 backend。
