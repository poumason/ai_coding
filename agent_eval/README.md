# agent-eval

針對「log 在 Langfuse 裡的 agent」做 golden-set 萃取 + 上線前模擬測試的小工具。
目標:每次改動 agent(換 prompt、換 skill、換 MCP tool)之前,都能拿一批真實對話
重播一次,看分數有沒有退步,而不是憑感覺判斷。

被測試的 agent 本身**不在這個 repo 裡**——它是任何一個把對話 log 到同一個
Langfuse project 的正式系統。這個工具只負責:(1) 從 Langfuse 撈資料做成
golden set、(2) 用一個可替換的 adapter 去呼叫那個 agent 並打分數。

## 文件導覽

這份 README 只放最短的快速開始;完整的分步驟說明在 `docs/` 底下:

1. [`docs/01-golden-set.md`](docs/01-golden-set.md) —
   怎麼從 Langfuse 撈 production trace、人工審核、發布成 golden set
2. [`docs/02-simulation.md`](docs/02-simulation.md) —
   怎麼用 golden set 做上線前模擬測試、兩種評分器怎麼算分、怎麼接 CI
3. [`docs/03-architecture.md`](docs/03-architecture.md) —
   整體架構、每個檔案負責什麼、目前還需要你確認/補上的事項

## 快速開始

```bash
cd agent_eval
uv sync
cp .env.example .env   # 填入 LANGFUSE_* 跟 AGENT_ENDPOINT
```

```bash
# 1. 從 production trace 撈候選資料
uv run agent-eval extract-candidates --name support-v1 \
    --from 2026-09-01 --to 2026-10-01 --tag prod --limit 200

# 2. 打開 data/golden_sets/support-v1/candidates.jsonl 人工審核,
#    把要留下的那幾筆 "status" 改成 "approved",再發布
uv run agent-eval publish-golden-set --name support-v1

# 3. 改動 agent 之後,拿這批 golden set 重播一次並打分數
uv run agent-eval run-simulation --dataset support-v1 \
    --agent-endpoint https://staging.example.com/agent/invoke \
    --run-name "pr-123-new-mcp-tool" --fail-under 0.8
```

每一步在做什麼、資料結構長什麼樣、分數怎麼算,請看上面的 `docs/`。
