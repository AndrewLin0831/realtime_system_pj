# Task Model Generator

This project implements an object-oriented Task Model Generator for real-time
systems, supporting periodic, sporadic, and aperiodic tasks. It is modular and
supports optional task attributes such as preemption, priority, and dependency.

---

## 🚀 Features

### ✔ Basic Task Types
The generator produces task sets containing:

- **Periodic Tasks**
  - arrival_time (phase)
  - execution_time
  - period
  - deadline

- **Sporadic Tasks**
  - arrival_time
  - execution_time
  - deadline
  - min_interval

- **Aperiodic Tasks**
  - arrival_time
  - execution_time
  - deadline

---

### ✔ Optional Advanced Attributes
Each attribute can be individually enabled or disabled:

| Attribute   | Description                        | Default |
|------------|------------------------------------|---------|
| preemption | Whether the task is preemptive     | False   |
| priority   | Task priority (lower = higher prio)| False   |
| dependency | List of tasks this task depends on | False   |

Enable them when creating the generator:

```python
gen = TaskSetGenerator(
    use_preemption=True,
    use_priority=True,
    use_dependency=True
)
```

---

## Example Usage
```python
from task_generator import TaskSetGenerator

gen = TaskSetGenerator(
    use_preemption=True,
    use_priority=True,
    use_dependency=False
)

task_set = gen.generate_task_set(
    np=3,   # number of periodic tasks
    ns=2,   # number of sporadic tasks
    na=2    # number of aperiodic tasks
)
```

---

## Output Format (Example)
```json
{
    "periodic": {
        "p1": {
            "arrival_time": 0,
            "period": 12,
            "execution_time": 2,
            "deadline": 10,
            "preemptive": true,
            "priority": 4,
            "dependency": []
        }
    },
    "aperiodic": {
        "a1": {
            "arrival_time": 20,
            "execution_time": 2,
            "deadline": 35
        }
    },
    "sporadic": {
        "s1": {
            "arrival_time": 40,
            "execution_time": 3,
            "deadline": 60,
            "min_interval": 8
        }
    }
}
```
Pretty printing:
```python
import json
print(json.dumps(task_set, indent=4))
```

