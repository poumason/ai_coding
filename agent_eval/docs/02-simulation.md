# 上線前模擬測試:`run-simulation`

這份文件說明 `run-simulation` 指令,對應
`src/agent_eval/simulate/run.py`,以及它用到的
`adapters/`、`judge.py`、`structural.py`、`tool_calls.py`。

## 整體流程

```
golden set(Langfuse Dataset)
        │
        ▼
for 每一筆 item:
        │
        ├─ AgentAdapter.invoke(input) ──> 呼叫你的 agent,拿到回覆 + tool calls
        │
        ├─ llm_judge_evaluator      ──> 用 Claude 比對「新回覆」vs「golden 答案」,給 0~1 分
        ├─ structural_evaluator     ──> 比對「實際呼叫的 tool」vs「golden 預期的 tool」,給 0~1 分
        │
        ▼
Langfuse 的 dataset.run_experiment(...) 自動把每一筆分數寫回 Langfuse,
變成一個可以在 UI 上跟其他次 run 比較的 Dataset Run
        │
        ▼
average_score_evaluator 把全部分數平均成一個 aggregate_score,
用來決定這次 --fail-under 要不要讓 CLI 回傳失敗的 exit code
```

這裡刻意沒有自己手刻「怎麼把分數寫回 Langfuse、怎麼建立可比較的 run」
這件事,而是直接用 Langfuse SDK 內建的實驗跑法
`dataset.run_experiment(task=..., evaluators=[...], run_evaluators=[...])`
——這個 API 的所有參數名稱、回傳結構(`ExperimentResult.item_results`、
`ExperimentResult.run_evaluations`、`ExperimentItemResult.item/.output/.evaluations`)
都已經對照安裝好的 `langfuse==5.0.4` 原始碼
(`site-packages/langfuse/experiment.py`)確認過。

## 指令

```bash
uv run agent-eval run-simulation --dataset support-v1 \
    --agent-endpoint https://staging.example.com/agent/invoke \
    --run-name "pr-123-new-mcp-tool" \
    --fail-under 0.8 \
    --tool-calls-from direct \
    --max-concurrency 5
```

| 參數 | 說明 |
|---|---|
| `--dataset` | 要重播的 golden set 名字(= Langfuse Dataset 名字)|
| `--agent-endpoint` | 你的 agent API(沒給的話用 `.env` 裡的 `AGENT_ENDPOINT`)|
| `--run-name` | 這次跑的標籤,會變成 Langfuse 上這個 Dataset Run 的名字,建議放 PR 號/commit sha |
| `--fail-under` | aggregate_score 低於這個值,CLI 回傳非 0 exit code(給未來接 CI 用)|
| `--tool-calls-from` | `direct`(預設,信任 agent API 回的 tool_calls)或 `langfuse`(見下方)|
| `--max-concurrency` | 同時打幾個 request 給 agent |

## Adapter:怎麼接上你真正的 agent

`src/agent_eval/simulate/adapters/base.py` 定義了這個介面:

```python
class AgentAdapter(Protocol):
    async def invoke(self, *, input: dict, correlation_id: str) -> AgentResult: ...
```

`http_adapter.py` 是一個「假設你的 agent 是個 JSON-over-HTTP API」的參考實作,
目前預設:

- Request: `POST {"input": <golden case 的 input>, "correlation_id": "<uuid>"}`,
  header 帶 `Authorization: Bearer <AGENT_API_KEY>`
- Response: `{"output": "<文字>", "tool_calls": [{"name": ..., "input": ...}, ...]}`

**這一定要照你真正的 agent API 改**——目前只是範例,還沒對過你實際系統的
欄位名稱。等你確認好 request/response 長怎樣,就回來改
`HttpAgentAdapter.invoke()` 裡面那幾行;如果你的 agent 不是 HTTP API
(例如是個 Python function、gRPC 等),就寫一個新的 class 實作同樣的
`invoke()` 介面,然後在 `cli.py` 裡換掉 `HttpAgentAdapter(...)` 那一行。

## 兩種 tool-call 來源(`--tool-calls-from`)

structural scorer 需要知道「agent 這次實際呼叫了哪些 tool」,有兩種拿法:

1. **`direct`**(預設,`simulate/tool_calls.py` 的 `DirectSource`):直接信任
   adapter 回應裡的 `tool_calls` 欄位。前提是你的 agent API 本來就會回傳
   這個資訊——你確認過是會回的,所以這是目前預設且正確的選擇。
2. **`langfuse`**(`LangfuseTraceLookupSource`):如果 agent API 只回最終
   文字、不回 tool call 清單,改用這個策略——它會拿 `correlation_id` 去
   Langfuse 查「被打上這個 tag 的 trace」,讀那個 trace 底下非 root
   observation 的名字/輸入當作實際 tool call 清單。**前提是你的 staging
   agent 自己也要把 Langfuse trace 打上這個 correlation_id 當 tag**,這點
   需要跟維護那個 agent 的人確認。

## 兩個評分器算分邏輯

### `llm_judge`(`simulate/judge.py`)

把「使用者輸入 / golden 標準答案 / agent 這次的回覆」丟給 Claude
(模型由 `.env` 的 `JUDGE_MODEL` 決定),請它用同一種語言給一句話理由加
0.0~1.0 分,標準是「這次回覆跟標準答案比,內容/結論/語氣是不是至少一樣好」
——用詞不同不扣分,答錯/沒解決問題才扣分。

### `tool_call_match`(`simulate/structural.py`)

比對「golden 預期的 tool 呼叫順序」跟「實際呼叫順序」:

- 完全沒預期也沒實際呼叫 tool → 1.0
- 名字、順序完全一樣:
  - 參數也完全一樣 → 1.0
  - 參數不一樣 → 0.75,並在 comment 裡列出哪幾個 tool 的參數對不上
- 名字或順序不一樣 → 用「預期 tool 集合」跟「實際 tool 集合」的重疊比例
  算分,再乘 0.5 封頂(代表「順序/內容錯了」最高只能拿到接近 0.5 分),
  comment 會列出「少呼叫了哪些」「多呼叫了哪些」

### `aggregate_score`(run-level,`average_score_evaluator`)

把這次 run 裡**所有**評分器、**所有**案例的分數攤平平均。這個平均值會
同時出現在 Langfuse 的 Dataset Run 上,以及 CLI 判斷 `--fail-under` 要不要
讓這次執行失敗。

## 輸出結果去哪裡看

1. 終端機:`result.format()` 的文字摘要 + 一張 rich table(總筆數、
   aggregate_score),以及(如果能解析出 project id)一個直接連到
   Langfuse UI 這次 Dataset Run 的連結。
2. Langfuse UI:該 Dataset 的「Experiments / Dataset Runs」頁面,可以跟
   之前任何一次 run 並排比較每一筆、每一個分數。
3. JSON 報告:`data/golden_sets/<name>/reports/<run-name>.json`,內容是
   每一筆案例的 `item_id`、`trace_id`、各評分器的 `scores`/`comments`,
   方便之後寫腳本再加工或存檔。

## 之後接 CI

`run-simulation` 的 exit code 已經代表成功/失敗(靠 `--fail-under`),所以
接 CI 不需要再寫新程式,只要加一個 workflow step:

```yaml
- name: Agent golden-set simulation
  run: |
    cd agent_eval
    uv sync
    uv run agent-eval run-simulation --dataset support-v1 \
      --agent-endpoint ${{ secrets.STAGING_AGENT_ENDPOINT }} \
      --run-name "ci-${{ github.sha }}" --fail-under 0.8
  env:
    LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
    LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
    ANTHROPIC_AUTH_TOKEN: ${{ secrets.ANTHROPIC_AUTH_TOKEN }}
```

條件是要有一個 CI 能打到的 staging agent endpoint——目前這部分還沒做,
是故意留到手動流程確認沒問題之後再接。
