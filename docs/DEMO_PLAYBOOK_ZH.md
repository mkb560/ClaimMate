# ClaimMate Demo Playbook

这份文档用于固定当前最适合展示的 demo 路径、问题顺序和展示重点，避免现场 demo 时临时发挥。

## 当前最稳定的 demo 资源

当前最适合 demo 的 3 个 `case_id`：

| case_id | 文件 | 类型 | 适合展示什么 |
|---|---|---|---|
| `allstate-change-2025-05` | `TEMP_PDF_FILE.pdf` | Allstate policy change packet | policyholders、policy number、policy change、生效日、discount |
| `allstate-renewal-2025-08` | `TEMP_PDF_FILE 2.pdf` | Allstate renewal packet | renewal package、optional coverage、法规时限 |
| `progressive-verification-2026-03` | `Verification of Insurance.pdf` | Progressive verification letter | policy period、insurer、verification vs full policy、15-day rule |

这 3 份 demo policy PDF 现在统一放在仓库根目录的 `demo_policy_pdfs/`，和 `claimmate_rag_docs/` 分开，避免被误当成 KB-B 法规资料一起索引。

如果你不想每次手动上传 PDF，现在也可以直接用：

- `POST /cases/{case_id}/demo/seed-policy`
- `backend/scripts/seed_demo_policy.py`

对于这 3 个固定 `case_id`，route 可以直接空 body 调用；如果想把固定 demo PDF 种到自定义 `case_id`，再显式传 `policy_key`。

## 固定 demo 顺序

推荐现场演示顺序：

1. 先展示上传过的真实保单 PDF
2. 先问一个“从保单里直接抽字段”的问题
3. 再问一个“保单 + 法规混合”的问题
4. 最后强调 citations 和 grounded answer

原因：
- 第一问最容易让老师立刻理解“它真的读懂了保单”
- 第二问能展示不是单纯 OCR 检索，而是 policy + regulation 联动
- citations 最后展示更容易形成可信度

## 固定 demo 问题

### Case 1: `allstate-change-2025-05`

推荐先问：

1. `Who are the policyholders and what is the policy number?`
2. `What policy change is confirmed and when is it effective?`
3. `What discount savings are listed for this policy period?`

想让观众看到的点：
- 能抽出 `Anlan Cai`、`Mingtao Ding`
- 能识别 `policy number`
- 能答出变更内容和生效日
- 能答出折扣总额

### Case 2: `allstate-renewal-2025-08`

推荐问题：

1. `What kind of insurance packet is this and who are the policyholders?`
2. `What optional coverage is highlighted in this renewal offer?`
3. `What should the insurer do within 15 days after receiving notice of claim?`

想让观众看到的点：
- 能识别 renewal packet
- 能识别 optional coverage
- 能跨 KB-A / KB-B 回答 California 时限

### Case 3: `progressive-verification-2026-03`

推荐问题：

1. `What is the policy number, policy period, and insurer?`
2. `Does this document say it is a full insurance policy or only verification of insurance?`
3. `What is the 15-day acknowledgment rule for a California claim?`

想让观众看到的点：
- 能区分 verification 和 full policy
- 能识别 insurer、policy period
- 能把法规说明讲清楚

## 当前最推荐的现场 demo 路径

最稳的一套是：

1. 先用 `allstate-change-2025-05` 展示结构化抽取
2. 再用 `allstate-renewal-2025-08` 展示法规联动
3. 最后用 `progressive-verification-2026-03` 展示“文档类型识别”

这样 3 个案例各自承担不同亮点，不会显得重复。

## 如何快速验证 demo 还是好的

本地可以直接跑：

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
export OPENAI_API_KEY="your_key"
python scripts/run_demo_eval.py --json-out /tmp/claimmate_demo_eval.json
```

当前 `run_demo_eval.py` 会默认使用仓库根目录 `demo_policy_pdfs/` 里的 3 份固定 demo PDF。

- 如果本地数据库里还没有 KB-B，脚本会先自动把仓库根目录 `claimmate_rag_docs/` 建成 KB-B
- 如果对应 `case_id` 还没有索引，脚本会自动 ingest
- 如果已经有 KB-B 或该 `case_id` 已经有 KB-A chunks，脚本会直接复用已有索引，避免重复 embedding 成本
- 如果你想强制替换其中某一份 policy，可以继续用 `--ingest-policy CASE_ID=/absolute/path/to/policy.pdf`
- 脚本仍然需要可用的 `DATABASE_URL` 和有额度的 `OPENAI_API_KEY`；现在如果缺数据库配置或 OpenAI quota 不足，会给出可读错误，而不是直接抛长 traceback

如果 `9/9 passed`，说明当前 demo 题集还是稳定的。

如果你只是想现场快速把某个 demo case 准备好，也可以直接跑：

```bash
cd backend
./.venv/bin/python scripts/seed_demo_policy.py --case-id allstate-change-2025-05
```

如果你想在 demo 前做一轮“整条 HTTP 路径都没坏”的检查，也可以跑：

```bash
cd backend
./.venv/bin/python scripts/run_demo_smoke.py --base-url http://127.0.0.1:8000
```

## Citation 展示建议

前端展示 citations 时，建议这样做：

1. 先显示 `source_label`
2. 再显示 `policy` 或 `regulatory` 标签
3. 再显示 `page_num`
4. `section` 只有在可读时才显示
5. excerpt 最多显示 1 到 2 行

推荐展示格式：

```text
Your Policy (TEMP_PDF_FILE.pdf) | Policy | Page 1
10 CCR 2695.5 Duties Upon Receipt of Communications | Regulatory | Page 1 | §2695.5
```

不要把 citation 做得比答案还大。它的作用是“增强可信度”，不是让用户先读 citation。

## 当前 demo 讲解口径

推荐你在现场这样解释：

- ClaimMate 先读取用户自己的 policy PDF
- 同时把 California claim regulations 做成共享知识库
- 回答时会优先从 policy 里提取结构化事实
- 对 policy metadata 类问题，系统会优先走 deterministic extraction；如果已索引 policy chunks 足够，甚至会直接跳过 embedding/LLM，减少 demo 时的回答漂移
- 如果问题涉及法规义务或理赔时限，会联动 regulatory corpus
- 最终答案带 citations，方便用户知道依据来自哪里
