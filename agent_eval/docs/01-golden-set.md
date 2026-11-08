# Golden Set:從 Langfuse 萃取、人工審核、發布

這份文件說明 `extract-candidates` 跟 `publish-golden-set` 兩個指令,對應
`src/agent_eval/golden_set/extract.py` 跟 `publish.py`。

## 背景概念

- 你的 agent 每處理一次對話,Langfuse 都會記一筆 **trace**;trace 底下會有
  一到多個 **observation**(每個 observation 代表一個步驟,例如一次 LLM
  呼叫、一次 tool/skill 呼叫)。
- 我們把「一個 trace = 一個對話回合」當作 golden set 的最小單位:
  trace 的**根 observation**(沒有 parent,或被標成 `is_root_observation`)
  的 input/output,當作這筆測試案例的「使用者輸入」跟「標準答案」;
  其他子 observation 則被當成這回合**應該呼叫的 tool/skill 清單**。

  ```
  trace (一次對話回合)
  ├─ root observation ──> GoldenCase.input / expected_output
  ├─ child observation (tool A) ──> expected_tool_calls[0]
  └─ child observation (tool B) ──> expected_tool_calls[1]
  ```

- 這整套萃取邏輯是用 Langfuse 的 **Observations API v2**
  (`client.api.observations.get_many`)寫的,不是舊版 `/api/public/traces`
  ——那個舊 API Langfuse 已經公告 2026-11-16 要關掉。所有欄位名稱
  (`trace_id`、`is_root_observation`、`parent_observation_id`、`tags`...)
  都已經對照安裝好的 `langfuse==5.0.4` 原始碼確認過,不是憑文件猜的。

## 步驟 1:`extract-candidates`

```bash
uv run agent-eval extract-candidates --name support-v1 \
    --from 2026-09-01 --to 2026-10-01 --tag prod --limit 200
```

參數:

| 參數       | 說明                                               |
|-----------|----------------------------------------------------|
| `--name`  | golden set 的名字,之後 publish / run-simulation 都會用到 |
| `--from` / `--to` | 要撈的時間範圍(`YYYY-MM-DD`,內部轉成 UTC)        |
| `--tag`   | 只撈有這個 Langfuse tag 的對話,可重複(`--tag prod --tag vip`)|
| `--limit` | 最多重建多少個**不同對話**(不是 observation 數量)   |

做了什麼事:

1. 用 `from_start_time`/`to_start_time`/`filter`(tag 篩選用的 JSON 結構化
   filter,不是直接傳 `tags=` 參數,因為 Observations API v2 沒有那個
   kwarg)呼叫 Langfuse,拿回一批 observation。
2. 依 `trace_id` 分組,每組重建成一筆 `GoldenCase`(定義在
   `src/agent_eval/schema.py`)。
3. 寫到 `data/golden_sets/<name>/candidates.jsonl`,一行一筆 JSON,預設
   `"status": "candidate"`。

`GoldenCase` 的欄位:

```jsonc
{
  "id": "uuid",                     // 這筆案例的 id(之後也是 Langfuse dataset item 的 id)
  "source_trace_id": "...",         // 來源 trace,方便回查原始對話
  "input": {"messages": [...]},      // 使用者輸入
  "expected_output": {"text": "..."}, // 標準答案(來自 root observation 的 output)
  "expected_tool_calls": [{"name": "...", "input": {...}}, ...],
  "tags": ["prod", "vip"],
  "status": "candidate",            // candidate / approved / rejected
  "notes": "",                      // 審核時可以自己寫備註
  "extracted_at": "...",
  "metadata": {...}
}
```

## 步驟 2:人工審核 `candidates.jsonl`

這一步**沒有指令**,就是直接打開
`data/golden_sets/support-v1/candidates.jsonl` 用文字編輯器改:

- 覺得 `expected_output.text` 寫得不夠好 → 直接改成你覺得對的答案。
- `expected_tool_calls` 抓錯/漏抓 → 直接增刪那個陣列。
- 這筆對話根本不適合當測試案例 → 整行刪掉,或留著但
  `"status": "rejected"`(兩種效果一樣,`publish` 只認 `"approved"`)。
- 覺得這筆沒問題、要放進 golden set → 把 `"status"` 改成 `"approved"`。

**沒有被改成 `"approved"` 的案例,發布時會被跳過**,不會不小心把沒審過的
資料放進正式 golden set。

## 步驟 3:`publish-golden-set`

```bash
uv run agent-eval publish-golden-set --name support-v1
```

做了什麼事(`golden_set/publish.py`):

1. 讀 `candidates.jsonl`,只留 `status == "approved"` 的案例,其他的印出來
   說被跳過了幾筆。
2. 呼叫 `langfuse.create_dataset(name="support-v1", ...)` 建立(或沿用)
   一個 Langfuse Dataset。
3. 對每一筆案例呼叫 `langfuse.create_dataset_item(..., source_trace_id=...)`
   ——`source_trace_id` 讓這個 dataset item 在 Langfuse UI 上可以直接點回
   原始的 production trace。
4. 同時把這批 approved 案例寫一份**不可變**的快照到
   `data/golden_sets/support-v1/<UTC 時間戳>.jsonl`,並 commit 進 git。

### 為什麼存兩份?

- **Langfuse Dataset** 是「現在這一版 golden set」的來源,`run-simulation`
  實際重播的就是它,而且 Langfuse UI 本身就有「比較不同 Dataset Run 分數」
  的功能,不用自己做。
- **git 裡的 JSONL 快照**是歷史紀錄:下次有人改 golden set,PR diff 就能
  看出「這次新增/刪除了哪幾筆測試案例」,比起只看 Langfuse UI 更方便做
  code review。這份快照會包含真實使用者對話內容——目前的決定是**直接
  commit、不做遮罩**,因為這個 repo 跟 Langfuse project 視為同一個受控私有
  環境。如果之後這個假設變了(例如 repo 權限變寬),要先回來加遮罩再繼續
  用這個流程。

## 之後想重新整理 golden set 怎麼辦?

重新跑一次 `extract-candidates --name support-v1`(可以用不同的時間範圍
或 tag),人工審核後再 `publish-golden-set --name support-v1` 一次——
`create_dataset_item` 用 `id` 當 upsert 的 key,所以同名案例會被更新,
不會重複。
