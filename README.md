# Realtime System — Task Model Generator（完整說明）

這個專案為即時系統（Real-time Systems）提供一個物件導向的 Task Set 產生器與簡易排程模擬器，支援週期（Periodic）、散發（Sporadic）與非週期（Aperiodic）任務，以及可選的屬性：可搶佔（preemptive）、優先權（priority）與相依性（dependencies）。

主要檔案
- [task_generator.py](c:\Users\user\Desktop\realtime_system_hw\task_generator.py) — 產生任務集合的主要類別：[`TaskSetGenerator`](c:\Users\user\Desktop\realtime_system_hw\task_generator.py)
- [task.py](c:\Users\user\Desktop\realtime_system_hw\task.py) — 任務模型（`Task`、`PeriodicTask`、`SporadicTask`、`AperiodicTask`）與 `Job` 類別
- [scheduler.py](c:\Users\user\Desktop\realtime_system_hw\scheduler.py) — 排程器基底與多種演算法實作（FIFO / EDF / RM / LLF / DM / PriorityInheritance / SJF / MyAlgo）
- [main.py](c:\Users\user\Desktop\realtime_system_hw\main.py) — 範例程式：建立 task set、執行多個排程器並輸出 timeline 與 metrics
- [task_gen_test.py](c:\Users\user\Desktop\realtime_system_hw\task_gen_test.py) — 簡單測試產生器並以 JSON 印出結果

功能亮點
- 支援三類任務型態：Periodic / Sporadic / Aperiodic
- 可選屬性：preemptive、priority、dependencies（可在產生器建立時啟用）
- 多種常見排程演算法實作（含範例自訂演算法 MyAlgo）
- 模擬輸出包含 timeline（每時間點執行的 Job 名稱）與詳細效能指標（drop rate、miss rate、response time、jitter、cpu util、fairness 等）

快速開始（Windows / VS Code）
1. 開啟專案資料夾（已知路徑）
   c:\Users\user\Desktop\realtime_system_hw
2. 在 VS Code 的整合終端機執行：
   python main.py
3. main.py 會產生 task set、執行一組 scheduler，並在終端印出：
   - 每個演算法的 metrics
   - basic_task_set 與 advanced_task_set
   - scheduled_basic_tasks / scheduled_advanced_tasks

如何使用 TaskSetGenerator
```py
from task_generator import TaskSetGenerator
# 建立產生器（選擇是否啟用可搶佔、優先權、相依性）
gen = TaskSetGenerator(use_preemption=True, use_priority=True, use_dependency=True, max_periodic_util=0.75)
tasks = gen.generate_task_set(np=4, ns=2, na=2)
```
參考：[`TaskSetGenerator`](c:\Users\user\Desktop\realtime_system_hw\task_generator.py)

主要資料格式與輸出
- main.py 提供兩種輸出映射：
  - basic: period/min_interval/execution_time/deadline/arrival_time（適合簡單呈現）
  - advanced: 包含 preemptive、priority、dependencies 等欄位
- scheduler 回傳結構（在 [scheduler.py](c:\Users\user\Desktop\realtime_system_hw\scheduler.py) 定義）：
  {
    "timeline": [(t, "p1_0"), ...] 或 "IDLE",
    "metrics": { ... }  # evaluate() 的輸出
  }

執行環境
- Python 3.x（只使用標準函式庫：random / statistics / json / os 等）
- 在 VS Code 中直接使用整合終端機（Windows）:
  python main.py


