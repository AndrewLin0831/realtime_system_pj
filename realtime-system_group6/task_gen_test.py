import json
from task_generator import TaskSetGenerator

generator = TaskSetGenerator(use_dependency=True, use_preemption=True, use_priority=True)
task_list = generator.generate_task_set(5, 6, 8)

out = {"periodic": {}, "sporadic": {}, "aperiodic": {}}
for t in task_list:
    if t.name.startswith("p"):
        out["periodic"][t.name] = t.to_dict()
    elif t.name.startswith("s"):
        out["sporadic"][t.name] = t.to_dict()
    else:
        out["aperiodic"][t.name] = t.to_dict()

# 緊湊輸出（不換行每個元素）
print(json.dumps(out, separators=(',', ':'), ensure_ascii=False))



