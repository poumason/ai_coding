# 架構總覽 / 檔案對照表 / 還沒做完的事

## 目錄結構對照

```
agent_eval/
├── .env.example              # 需要哪些環境變數,見下方「環境變數」
├── pyproject.toml            # 依賴:langfuse, anthropic, typer, rich, pydantic, httpx
├── src/agent_eval/
│   ├── cli.py                 # 3 個指令的入口(extract-candidates / publish-golden-set / run-simulation)
│   ├── config.py              # 讀 .env,組出 Settings
│   ├── schema.py              # GoldenCase / ToolCall / CaseStatus 資料結構
│   ├── golden_set/
│   │   ├── extract.py         # 對應 docs/01 步驟 1:Langfuse -> candidates.jsonl
│   │   └── publish.py         # 對應 docs/01 步驟 3:candidates.jsonl -> Langfuse Dataset + git 快照
│   └── simulate/
│       ├── adapters/
│       │   ├── base.py        # AgentAdapter 介面定義
│       │   └── http_adapter.py # 參考實作,需要照你的 agent API 改
│       ├── tool_calls.py      # DirectSource / LangfuseTraceLookupSource
│       ├── judge.py           # LLM-as-judge 評分器
│       ├── structural.py      # tool call 結構比對評分器 + 平均分數的 run-level 評分器
│       └── run.py             # 對應 docs/02:把上面全部兜起來呼叫 dataset.run_experiment
└── data/golden_sets/<name>/
    ├── candidates.jsonl        # 萃取後、審核中的草稿
    ├── <timestamp>.jsonl       # 已發布版本的快照(commit 進 git)
    └── reports/<run-name>.json # 每次 run-simulation 的分數報告
```

## 資料怎麼流動

```
Langfuse (production traces)
        │  extract-candidates (Observations API v2)
        ▼
candidates.jsonl ──(人工審核、改 status)──> 還是 candidates.jsonl
        │  publish-golden-set
        ├──────────────────────────────┐
        ▼                              ▼
Langfuse Dataset "support-v1"    data/golden_sets/support-v1/<timestamp>.jsonl (git)
        │  run-simulation(呼叫你的 agent + 評分)
        ▼
Langfuse Dataset Run(UI 可比較歷史分數) + data/golden_sets/support-v1/reports/<run-name>.json
```

## 環境變數(`.env`)

| 變數 | 用途 |
|---|---|
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | 連到你的 Langfuse project |
| `AGENT_ENDPOINT` / `AGENT_API_KEY` | `HttpAgentAdapter` 預設呼叫的 agent API |
| `JUDGE_MODEL` | `llm_judge_evaluator` 用哪個 Claude 模型當裁判 |
| `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` | 如果你是走自己的 gateway 而不是直接打 api.anthropic.com |

## 這套工具驗證到什麼程度

已經驗證的部分(不需要你的正式帳密):

- 所有模組 import 正常,CLI 三個指令 `--help` 都能跑。
- 每一個用到的 Langfuse / Anthropic SDK 方法簽名,都對照已安裝的
  `langfuse==5.0.4`、`anthropic==1.17.0` 原始碼確認過參數名稱,不是照文件
  猜的(SDK 這部分在這套工具開發當下剛好有大改版,文件跟實際安裝版本偶爾
  會對不上,所以特別去讀了 site-packages 裡的原始碼)。
- `extract.py` 的 trace 重建邏輯、`structural.py` 的評分邏輯、
  `publish.py` 的審核過濾邏輯,都用假資料(手刻的 `ObservationV2`、
  `GoldenCase`)跑過,行為符合預期。

還沒驗證、需要你實際帳密才能做的部分:

- 真的打 Langfuse API 把資料撈出來、寫進去(`create_dataset`、
  `create_dataset_item`、`get_dataset`、`run_experiment` 的網路呼叫)。
- 真的呼叫你的 agent API(`HttpAgentAdapter`)。
- `llm_judge_evaluator` 真的呼叫 Claude(需要可用的 `ANTHROPIC_*` 設定)。

## 目前還欠你確認/補的事

1. **`http_adapter.py` 的真實欄位名稱** —— 目前的 request/response 欄位
   (`input` / `correlation_id` / `output` / `tool_calls`)是預設範例,
   還沒對過你實際 agent API 的 request/response schema。你已經確認過:
   - 認證方式是 Bearer token(跟目前預設一致,不用改)
   - response 裡本來就有 tool/skill 呼叫清單(所以 `--tool-calls-from direct`
     是對的,不需要用 `langfuse` lookup 那條路)

   還缺:request 裡使用者訊息放在哪個欄位、要不要帶 session/user id、
   response 裡最終文字放在哪個欄位、每個 tool call 物件長怎樣
   (`{"name", "input"}` 還是別的命名)。確認後改
   `src/agent_eval/simulate/adapters/http_adapter.py` 裡 `invoke()` 組
   request body 跟解析 response 那幾行就好,其他地方不用動。

2. **CI 串接** —— `docs/02-simulation.md` 最後那段 workflow 範例還沒真的
   加進 `.github/workflows/`,因為目前還沒有 CI 可以打到的 staging agent
   endpoint。等手動跑過 `run-simulation` 確認沒問題,再决定要不要加。

3. **第一批 golden set** —— 工具寫好了,但還沒有人實際跑過
   `extract-candidates` 對著你的正式 Langfuse project 撈過真資料、審核過、
   發布成第一個 golden set。
