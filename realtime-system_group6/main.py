# main.py
import json
from task_generator import TaskSetGenerator
from scheduler import (
    FIFOScheduler, EDFScheduler, RMScheduler,
    LLFScheduler, DMScheduler, PriorityInheritanceScheduler,
    SJFScheduler, MyAlgoScheduler
)
import os
import json
import eval

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
def save_custom_compact_format(filepath: str, data: dict):
    """
    將 Python 字典（假設值可能是列表）以自定義的緊湊且類似 Python 字典定義的格式儲存到檔案。
    
    格式範例：
    varname = {
        "key1": [1, 2, 3],
        "key2": 'value',
    }
    
    Args:
        filepath: 儲存 JSON 檔案的路徑。
        data: 要儲存的 Python 字典。
    """
    
    # 確保目錄存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            # 寫入字典起始行
            f.write("basic_schedule_output = {\n")
            
            items = list(data.items())
            for i, (k, v) in enumerate(items):
                comma = "," if i < len(items) - 1 else ""
                
                # 這裡使用 repr(v) 來渲染列表為單行字串，
                # 同時保持其他數值的原始表示 (例如數字不需要引號)
                # 注意：這輸出的不是標準 JSON，而是 Python 字典字串表示。
                
                # 由於 repr(v) 對於字串會使用單引號，這更符合您的範例函式行為，
                # 但如果需要標準 JSON 字串，則需換用 json.dumps(v, separators=(',', ':'))。
                # 這裡遵循您提供的 _print_compact_dict_of_lists 邏輯。
                
                # 處理鍵名
                key_str = f'    "{k}":'
                
                # 處理值
                if isinstance(v, (int, float, bool)):
                    value_str = str(v)
                elif isinstance(v, (list, dict)):
                    # 對於列表和字典，使用 json.dumps 獲得緊湊的 JSON 字串
                    # 這是最可靠的方式，避免 repr() 產生的單引號不符合 JSON 標準
                    value_str = json.dumps(v, ensure_ascii=False, separators=(',', ':'))
                else:
                    # 處理字串，讓它看起來像 Python 字串
                    value_str = repr(v) 

                f.write(f"{key_str}{value_str}{comma}\n")
                
            # 寫入字典結束行
            f.write("}\n")
            
        # print(f"成功以自定義緊湊格式儲存檔案到: {filepath}")
    except Exception as e:
        print(f"儲存檔案時發生錯誤: {e}")
        

def tasks_to_basic_dict(tasks):
    out = {"periodic": {}, "aperiodic": {}, "sporadic": {}}
    for t in tasks:
        if t.name.startswith("p"):
            out["periodic"][t.name] = {"arrival_time": t.arrival_time, "period": t.period, "execution_time": t.exec_time, "deadline": t.deadline}
        elif t.name.startswith("s"):
            out["sporadic"][t.name] = {"arrival_time": t.arrival_time, "execution_time": t.exec_time, "deadline": t.deadline, "min_interval": getattr(t, "interval", getattr(t, "min_interval", None))}
        else:
            out["aperiodic"][t.name] = {"arrival_time": t.arrival_time, "execution_time": t.exec_time, "deadline": t.deadline}
    return out

def tasks_to_advanced_dict(tasks):
    out = {"periodic": {}, "aperiodic": {}, "sporadic": {}}
    for t in tasks:
        common = {"arrival_time": t.arrival_time, "execution_time": t.exec_time, "deadline": t.deadline, "priority": getattr(t, "priority", None), "preemptive": getattr(t, "preemptive", None), "dependencies": getattr(t, "dependencies", []) or getattr(t, "dependency", []) or []}
        if t.name.startswith("p"):
            d = dict(common); d["period"] = t.period; out["periodic"][t.name] = d
        elif t.name.startswith("s"):
            d = dict(common); d["min_interval"] = getattr(t, "interval", getattr(t, "min_interval", None)); out["sporadic"][t.name] = d
        else:
            out["aperiodic"][t.name] = dict(common)
    return out

def timeline_names_from_result(result):
    names = []
    for entry in result.get("timeline", []):
        n = entry[1] if isinstance(entry, (list, tuple)) else entry
        if isinstance(n, str) and n.upper() == "IDLE":
            names.append("idle")
        else:
            # Job.name may be like "p1_0" -> extract base task name
            base = n.split('_')[0] if isinstance(n, str) and '_' in n else n
            names.append(base)
    return names

def _print_compact_dict_of_lists(varname, d):
    print(f"{varname} = {{")
    items = list(d.items())
    for i, (k, v) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        # use repr(v) to render lists as single-line with single quotes (符合範例)
        print(f'    "{k}":{repr(v)}{comma}')
    print("}")



def main():
    # ------------------------
    # Settings
    # ------------------------
    NP = 5
    NS = 5
    NA = 4
    sim_time = 100

    gen_basic = TaskSetGenerator(
        use_dependency=False,
        use_preemption=False,
        use_priority=False,
        max_periodic_util=0.7,
    )

    gen_advance = TaskSetGenerator(
        use_dependency=True,
        use_preemption=True,
        use_priority=True,
        max_periodic_util=0.75,
    )

    tasks_basic = gen_basic.generate_task_set(NP, NS, NA)
    tasks_advance = gen_advance.generate_task_set(NP, NS, NA)

    basic_task_set = tasks_to_basic_dict(tasks_basic)
    advanced_task_set = tasks_to_advanced_dict(tasks_advance)

    schedulers = [
        FIFOScheduler(), EDFScheduler(), RMScheduler(),
        LLFScheduler(), DMScheduler(), PriorityInheritanceScheduler(),
        SJFScheduler(), MyAlgoScheduler()
    ]

    # ==================================================
    # BASIC
    # ==================================================
    basic_metrics = {}
    basic_schedule = {}

    print("----------- basic result -----------\n")
    for s in schedulers:
        res = s.run(tasks_basic, sim_time)
        key = "myAlgo" if s.name.lower().startswith("myalgo") else s.name

        basic_metrics[key] = res["metrics"]
        basic_schedule[key] = timeline_names_from_result(res)

        print(f"{key} Metrics: {json.dumps(res['metrics'], separators=(',',':'), ensure_ascii=False)}\n")

    # 輸出 Basic 檔案
    save_json("output/basic/task_set.json", basic_task_set)
    save_json("output/basic/metrics.json", basic_metrics)
    save_custom_compact_format("output/basic/schedule", basic_schedule)


    # ==================================================
    # ADVANCED
    # ==================================================
    advance_metrics = {}
    advance_schedule = {}

    print("----------- advance result -----------\n")
    for s in schedulers:
        res = s.run(tasks_advance, sim_time)
        key = "myAlgo" if s.name.lower().startswith("myalgo") else s.name

        advance_metrics[key] = res["metrics"]
        advance_schedule[key] = timeline_names_from_result(res)

        print(f"{key} Metrics: {json.dumps(res['metrics'], separators=(',',':'), ensure_ascii=False)}\n")

    # 輸出 Advanced 檔案
    save_json("output/advanced/task_set.json", advanced_task_set)
    save_json("output/advanced/metrics.json", advance_metrics)
    save_custom_compact_format("output/advanced/schedule", advance_schedule)
    print(advance_schedule)

    print("\n[INFO] All results saved to ./output/")
    
    

    

if __name__ == "__main__":
    main()