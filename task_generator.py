from task import PeriodicTask, SporadicTask, AperiodicTask
import random

class TaskSetGenerator:
    def __init__(self, use_preemption=False, use_priority=False, use_dependency=False, max_periodic_util=0.9):
        self.use_preemption = use_preemption
        self.use_priority = use_priority
        self.use_dependency = use_dependency
        self.all_task_names = []
        self.max_periodic_util = max_periodic_util

    def _add_optional_fields(self, all_task_names):
        preemptive = None
        priority = None
        dependencies = []
        if self.use_preemption:
            preemptive = random.choice([True, False])
        if self.use_priority:
            priority = random.randint(1, 10)
        if self.use_dependency and all_task_names and random.random() < 0.2:
            dep_count = random.randint(1, min(2, len(all_task_names)))
            dependencies = random.sample(all_task_names, dep_count)
        return preemptive, priority, dependencies

    def generate_periodic(self, n):
        tasks = []
        attempts = 0
        while True:
            attempts += 1
            tasks = []
            self.all_task_names = [name for name in self.all_task_names if not name.startswith("p")]
            for i in range(1, n+1):
                name = f"p{i}"
                self.all_task_names.append(name)
                arrival = random.randint(0, 10)
                exec_time = random.randint(1, 5)
                period = random.randint(max(5, exec_time+1), 25)
                deadline = random.randint(exec_time + 1, period)
                preemptive, priority, dep = self._add_optional_fields(self.all_task_names[:-1])
                t = PeriodicTask(name, arrival, exec_time, period, deadline, preemptive, priority, dep)
                tasks.append(t)
            util = sum(t.exec_time / t.period for t in tasks)
            if util <= self.max_periodic_util or attempts > 200:
                break
        return tasks

    def generate_sporadic(self, n):
        tasks = []
        for i in range(1, n+1):
            name = f"s{i}"
            self.all_task_names.append(name)
            arrival = random.randint(0, 50)
            exec_time = random.randint(1, 5)
            deadline = random.randint(exec_time + 5, 20)
            interval = random.randint(5, 12)
            preemptive, priority, dep = self._add_optional_fields(self.all_task_names[:-1])
            t = SporadicTask(name, arrival, exec_time, deadline, interval, preemptive, priority, dep)
            tasks.append(t)
        return tasks

    def generate_aperiodic(self, n):
        tasks = []
        for i in range(1, n+1):
            name = f"a{i}"
            self.all_task_names.append(name)
            arrival = random.randint(0, 50)
            exec_time = random.randint(1, 5)
            deadline = random.randint(exec_time + 5, 30)
            preemptive, priority, dep = self._add_optional_fields(self.all_task_names[:-1])
            t = AperiodicTask(name, arrival, exec_time, deadline, preemptive, priority, dep)
            tasks.append(t)
        return tasks

    def generate_task_set(self, np=3, ns=2, na=2):
        periodic = self.generate_periodic(np)
        sporadic = self.generate_sporadic(ns)
        aperiodic = self.generate_aperiodic(na)
        return periodic + sporadic + aperiodic
