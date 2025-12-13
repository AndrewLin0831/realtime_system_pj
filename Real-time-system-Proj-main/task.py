# task.py

class Task:
    def __init__(self, name, arrival, exec_time, deadline, 
                 preemptive=False, priority=0, dependencies=None):
        self.name = name
        self.arrival_time = arrival
        self.exec_time = exec_time
        self.deadline = deadline  # Relative Deadline
        self.preemptive = preemptive
        self.priority = priority
        self.dependencies = dependencies if dependencies else []

class PeriodicTask(Task):
    def __init__(self, name, arrival, exec_time, period, deadline, 
                 preemptive=False, priority=0, dependencies=None):
        super().__init__(name, arrival, exec_time, deadline, 
                         preemptive, priority, dependencies)
        self.period = period
        self.task_type = "Periodic"

class SporadicTask(Task):
    def __init__(self, name, arrival, exec_time, deadline, interval, 
                 preemptive=False, priority=0, dependencies=None):
        super().__init__(name, arrival, exec_time, deadline, 
                         preemptive, priority, dependencies)
        self.interval = interval
        self.task_type = "Sporadic"

class AperiodicTask(Task):
    def __init__(self, name, arrival, exec_time, deadline, 
                 preemptive=False, priority=0, dependencies=None):
        super().__init__(name, arrival, exec_time, deadline, 
                         preemptive, priority, dependencies)
        self.task_type = "Aperiodic"

# ----------------------------------------------
# Job: 實際被排程執行的物件
# ----------------------------------------------
class Job:
    def __init__(self, task, release_time, abs_deadline):
        self.task = task
        self.name = f"{task.name}_{release_time}"
        self.release_time = release_time
        self.absolute_deadline = abs_deadline
        self.remaining_time = task.exec_time
        
        # 統計數據
        self.start_time = -1
        self.finish_time = -1
        self.is_completed = False
        self.is_missed = False

    @property
    def laxity(self):
        # Laxity = (Deadline - CurrentTime) - RemainingTime
        # 注意：這裡需要在外部減去 current_time
        return self.absolute_deadline - self.remaining_time