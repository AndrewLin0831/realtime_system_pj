from task import PeriodicTask, SporadicTask, AperiodicTask, Job
from EDFAcceptanceTest import EDFAcceptanceTest
from generate_tool import *
import random
import math

class TaskSetGenerator:
    def __init__(self, use_preemption=False, use_priority=False, use_dependency=False, max_periodic_util=0.7, SEED=42):
        self.use_preemption = use_preemption
        self.use_priority = use_priority
        self.use_dependency = use_dependency
        self.all_task_names = []
        self.max_periodic_util = max_periodic_util
        random.seed(77)

    def _add_optional_fields(self, existing_tasks, my_arrival):
        preemptive = None
        priority = None
        dependencies = []
        if self.use_preemption:
            # preemptive = random.choice([True, False])
            preemptive = True
        if self.use_priority:
            priority = random.randint(1, 10)
        if self.use_dependency:
            eligible = [t.name for t in existing_tasks if t.arrival_time <= my_arrival]
            if eligible and random.random() < 0.2:
                dep_count = random.randint(1, min(2, len(eligible)))
                dependencies = random.sample(eligible, dep_count)
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
                
                # arrival = random.randint(0, 5)
                arrival = 0
                
                exec_time = random.randint(1, 3)
                period = random.randint(max(10, exec_time+6), 25)
                
                deadline = random.randint(int(period*0.8), period)

                # deadline = exec_time + 1
                
                preemptive, priority, dep = self._add_optional_fields(tasks, arrival)

                t = PeriodicTask(name, arrival, exec_time, period, deadline, preemptive, priority, [])
                tasks.append(t)
            # ---------- Step 1: 利用率前置過濾 ----------
            util = sum(t.exec_time / t.period for t in tasks)

            if util > self.max_periodic_util:
                # 太重了，不可能排程，直接跳過，不做 RTA
                continue

            # ---------- Step 2: 使用 RM RTA 完整可排程性檢查 ----------
            if self.check_schedulable_RM_RTA(tasks):
                print(f"[INFO] Found schedulable periodic task set in {attempts} attempts.")
                return tasks

            if attempts > 500:
                print("[WARN] Could not find schedulable task set, returning best-effort set.")
                return tasks
        return tasks

    def generate_sporadic(self, n, start_idx=1):
        tasks = []
        for i in range(start_idx, start_idx + n):
            name = f"s{i}"
            self.all_task_names.append(name)
            arrival = random.randint(0, 50)
            # arrival = 5
            
            exec_time = random.randint(1, 3)
            deadline = random.randint(15, 30)
            
            # 極端情況
            # deadline = exec_time + 1
            
            interval = random.randint(5, 12)
            preemptive, priority, dep = self._add_optional_fields(tasks, arrival)
            t = SporadicTask(name, arrival, exec_time, deadline, interval, preemptive, priority, [])
            tasks.append(t)
        return tasks

    def generate_aperiodic(self, n):
        tasks = []
        for i in range(1, n+1):
            name = f"a{i}"
            self.all_task_names.append(name)
            arrival = random.randint(0, 50)
            exec_time = random.randint(1, 3)
            deadline = random.randint(exec_time + 5, 30)
            preemptive, priority, dep = self._add_optional_fields(tasks, arrival)
            t = AperiodicTask(name, arrival, exec_time, deadline, preemptive, priority, dep)
            tasks.append(t)
        return tasks


    
    def generate_task_set(self, np=3, ns=2, na=2):
        periodic = self.generate_periodic(np)
        aperiodic = self.generate_aperiodic(na)

        admission = EDFAcceptanceTest(periodic_tasks=periodic)
        admitted_sporadic_tasks = []
        next_sid = 1

        while len(admitted_sporadic_tasks) < ns:
            s = self.generate_sporadic(1, start_idx=next_sid)[0]

            # 用「假 job」只做 admission test
            fake_job = Job(
                task=s,
                release_time=s.arrival_time,
                abs_deadline=s.arrival_time + s.deadline,
            )

            if admission.accept(
                new_job=fake_job,
                admitted_sporadic_jobs=[],
                now=s.arrival_time
            ):
                next_sid += 1
                admitted_sporadic_tasks.append(s)

        return periodic + admitted_sporadic_tasks + aperiodic
    
    
    '''
    def generate_task_set(self, np=3, ns=2, na=2):
        periodic = self.generate_periodic(np)

        # soft tasks 不影響 hard guarantee（要 hard=0，就別讓 soft 影響 hard）
        aperiodic = self.generate_aperiodic(na)

        admission = EDFAcceptanceTest(periodic_tasks=periodic)

        admitted_sporadic_tasks = []
        admitted_fake_jobs = []   # 用 job 存 admitted hard sporadic，給 acceptance 算 demand

        next_sid = 1
        guard = 0

        while len(admitted_sporadic_tasks) < ns and guard < 2000:
            guard += 1
            s = self.generate_sporadic(1, start_idx=next_sid)[0]

            fake_job = Job(
                task=s,
                release_time=s.arrival_time,
                abs_deadline=s.arrival_time + s.deadline,
            )

            # 重點：admitted_fake_jobs 要傳進去，而不是 []
            # 更保守：now 用 0 做 worst-case（避免 backlog/carry-in 你離線算不到）
            if admission.accept(
                new_job=fake_job,
                admitted_sporadic_jobs=admitted_fake_jobs,
                now=0
            ):
                admitted_sporadic_tasks.append(s)
                admitted_fake_jobs.append(fake_job)
                next_sid += 1
            else:
                # reject: 不加 next_sid，避免跳號也行（看你要不要）
                next_sid += 1

        return periodic + admitted_sporadic_tasks + aperiodic
    '''
    
    
    
    def check_schedulable_RM_RTA(self, tasks):
        """
        tasks: list of PeriodicTask
        return: True if schedulable under RM
        """

        # RM priority：period 越小優先權越高
        tasks_sorted = sorted(tasks, key=lambda t: t.period)

        for i, ti in enumerate(tasks_sorted):

            Ci = ti.exec_time
            Di = ti.deadline  # typically = period
            Ri = Ci           # initial response time

            while True:
                # interference from higher-priority tasks
                interference = sum(
                    math.ceil(Ri / tj.period) * tj.exec_time
                    for tj in tasks_sorted[:i]  # higher priority tasks only
                )

                new_Ri = Ci + interference

                # Convergence
                if new_Ri == Ri:
                    break

                # If exceed deadline -> NOT schedulable
                if new_Ri > Di:
                    return False

                Ri = new_Ri

        return True


    
