# main.py
import json
from task_generator import TaskSetGenerator
from scheduler import (
    FIFOScheduler, EDFScheduler, RMScheduler,
    LLFScheduler, DMScheduler, PriorityInheritanceScheduler,
    SJFScheduler, MyAlgoScheduler
)

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
    gen = TaskSetGenerator(use_dependency=True, use_preemption=True, use_priority=True, max_periodic_util=0.75)
    tasks = gen.generate_task_set(np=4, ns=2, na=2)

    basic_task_set = tasks_to_basic_dict(tasks)
    advanced_task_set = tasks_to_advanced_dict(tasks)

    schedulers = [
        FIFOScheduler(), EDFScheduler(), RMScheduler(),
        LLFScheduler(), DMScheduler(), PriorityInheritanceScheduler(),
        SJFScheduler(), MyAlgoScheduler()
    ]

    sim_time = 100
    scheduled_basic_tasks = {}
    scheduled_advanced_tasks = {}

    for s in schedulers:
        res = s.run(tasks, sim_time=sim_time)
        names = timeline_names_from_result(res)
        key = s.name
        if key.lower().startswith("myalgo"):
            key = "myAlgo"
        scheduled_basic_tasks[key] = names
        scheduled_advanced_tasks[key] = names
        # 列印每個演算法 metrics（緊湊）
        print(f"{key} Metrics: {json.dumps(res['metrics'], separators=(',',':'), ensure_ascii=False)}")

    # 顯示 basic / advanced task set（漂亮縮排）
    print("\nbasic_task_set =")
    print(json.dumps(basic_task_set, indent=4, ensure_ascii=False))
    print("\nadvanced_task_set =")
    print(json.dumps(advanced_task_set, indent=4, ensure_ascii=False))

    # 顯示 scheduled_*（keys 每行，lists 單行）
    print("\nGenerated Scheduled Basic Tasks :\n")
    _print_compact_dict_of_lists("scheduled_basic_tasks", scheduled_basic_tasks)

    print("\nGenerated Scheduled Advanced Tasks :\n")
    _print_compact_dict_of_lists("scheduled_advanced_tasks", scheduled_advanced_tasks)

if __name__ == "__main__":
    main()