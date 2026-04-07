# Technical Milestone 1 Video Script

## 开场

Hi, I’m Mingtao Ding, and this is Technical Milestone 1 for ClaimMate.

In this milestone, I’m focusing on the AI backend core of the project. Specifically, I will show live policy ingestion, grounded question answering, and a repeatable demo workflow using our backend APIs.

## 操作 + Script

推荐直接用 FastAPI Swagger 页面录制。

先打开：

- 本地后端：`http://127.0.0.1:8000/docs`
- 如果你想用 shared backend，就把地址换成对应的 `.../docs`

整个 demo 统一使用：

- `case_id = tm1-policy-demo`
- `policy_key = allstate-renewal`

### 1. 展示 `GET /health`

1. 在 `/docs` 页面找到 `GET /health`
2. 点开这一栏
3. 点 `Try it out`
4. 点 `Execute`
5. 停一下，让画面显示 response body

重点让老师看到：

- `"status": "ok"`
- `"ai_ready": true`

Script:

First, I’m checking the health endpoint.

This confirms that the backend is live and that the AI system is ready. Here, `status` is `ok`, and `ai_ready` is `true`, which means the system has initialized successfully.



### 2. 展示 `GET /demo/policies`

1. 找到 `GET /demo/policies`
2. 点开
3. 点 `Try it out`
4. 点 `Execute`
5. 停一下，让画面显示 `policies` 列表

重点让老师看到：

- `policy_key`
- `default_case_id`
- `label`
- `sample_questions`

Script:

Next, I’m calling the demo policy catalog endpoint.

This endpoint shows the built-in demo policy catalog.

It returns a list of sample insurance documents that I can use for testing and demo purposes.

Each item includes a policy key, a default case ID, a label, the file name, and some sample questions.

So this page is basically showing which demo policies are available before I load one into a case.

### 3. 展示 `POST /cases/{case_id}/demo/seed-policy`

1. 找到 `POST /cases/{case_id}/demo/seed-policy`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm1-policy-demo`
5. 在 request body 里填下面这段：

```json
{
  "policy_key": "allstate-renewal"
}
```

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `case_id`
- `policy_key`
- `label`
- `filename`
- `chunk_count`
- `status`

Script:

Now I’m seeding one demo policy into a fresh case.

This step seeds a demo insurance policy into a new case.

Here, tm1-policy-demo is the case ID, and allstate-renewal tells the system which sample policy to use.

After I click Execute, the backend loads that sample PDF, processes it, and indexes it so the system can answer questions about this policy.

In the response, we can see the case ID, the selected policy, the file name, the sample questions, the number of chunks created, and the final status indexed. That means the policy is now ready for question answering.”

At this step, the backend loads a real sample insurance policy into the case knowledge base. Behind the scenes, the system parses the document, chunks it, embeds it, and stores it for retrieval.

### 4. 展示 `GET /cases/{case_id}/policy`

1. 找到 `GET /cases/{case_id}/policy`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm1-policy-demo`
5. 点 `Execute`
6. 停一下，让画面显示 response body

重点让老师看到：

- `has_policy: true`
- `chunk_count`
- `filename`
- `demo_policy`

Script:

Here I’m verifying that the policy has been indexed successfully.

This endpoint uploads a real policy PDF for a case.

Here, I choose a file and send it to the backend for tm1-policy-demo.

After I click Execute, the system saves the file, processes the document, and indexes it for retrieval.

In the response, we can see the case ID, the file name, the number of chunks created, and the status indexed.

That means the uploaded policy is now ready for question answering.

### 5. 展示第一个 `POST /cases/{case_id}/ask`

1. 找到 `POST /cases/{case_id}/ask`
2. 点开
3. 点 `Try it out`
4. 在 `case_id` 里填：`tm1-policy-demo`
5. 在 request body 里填下面这段：

```json
{
  "question": "What is the policy number?"
}
```

6. 点 `Execute`
7. 停一下，让画面显示 response body

重点让老师看到：

- `question`
- `answer`
- `citations`

Script:

Now I’m asking a direct policy question: ‘What is the policy number?’

Here, the system reads the indexed policy for this case and returns a grounded answer.

For supported fact questions like this one, ClaimMate uses deterministic extraction before falling back to general generation. That makes the result more stable and more reliable for key policy details.

In the response, we can see the original question, the answer, and the citation showing where the information came from

### 6. 展示第二个 `POST /cases/{case_id}/ask`

还是同一个接口，再执行一次。

1. 保持 `case_id = tm1-policy-demo`
2. 把 request body 改成：

```json
{
  "question": "What is the California 15-day claim acknowledgment rule?"
}
```

3. 点 `Execute`
4. 停一下，让画面显示 response body

重点让老师看到：

- `answer`
- `citations`

Script:

Next, I’m asking a regulatory question: “What is the California 15-day claim acknowledgment rule?”

This demonstrates the retrieval-augmented generation pipeline. The system searches both the user’s policy and curated regulatory sources, then returns a grounded answer with citations.

One important part here is that the answer is not just generated text. It is tied back to source material through citations, which makes the output more trustworthy and easier to inspect.

### 7. 录制顺序

正式录的时候，按这个顺序来：

1. `GET /health`
2. `GET /demo/policies`
3. `POST /cases/tm1-policy-demo/demo/seed-policy`
4. `GET /cases/tm1-policy-demo/policy`
5. `POST /cases/tm1-policy-demo/ask`
   Question: `What is the policy number?`
6. `POST /cases/tm1-policy-demo/ask`
   Question: `What is the California 15-day claim acknowledgment rule?`

## 结尾

So, in Technical Milestone 1, I have demonstrated the core AI backend functionality of ClaimMate: document ingestion, policy understanding, grounded question answering, and repeatable demo support.

This milestone establishes the technical foundation for the broader claims assistance workflow in later milestones.
