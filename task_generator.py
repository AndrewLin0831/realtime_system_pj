from task import PeriodicTask, SporadicTask, AperiodicTask
import random
import math

class TaskSetGenerator:
    def __init__(self, use_preemption=False, use_priority=False, use_dependency=False, max_periodic_util=0.7, SEED=42):
        self.use_preemption = use_preemption
        self.use_priority = use_priority
        self.use_dependency = use_dependency
        self.all_task_names = []
        self.max_periodic_util = max_periodic_util
        # random.seed(SEED)

    def _add_optional_fields(self, all_task_names):
        preemptive = None
        priority = None
        dependencies = []
        if self.use_preemption:
            preemptive = random.choice([True, False])
            # preemptive = True
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
                
                arrival = random.randint(0, 5)
                # arrival = 0
                
                exec_time = random.randint(1, 3)
                period = random.randint(max(10, exec_time+6), 25)
                
                deadline = random.randint(int(period*0.8), period)

                # deadline = exec_time + 1
                
                preemptive, priority, dep = self._add_optional_fields(self.all_task_names[:-1])
                t = PeriodicTask(name, arrival, exec_time, period, deadline, True, priority, dep)
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

    def generate_sporadic(self, n):
        tasks = []
        for i in range(1, n+1):
            name = f"s{i}"
            self.all_task_names.append(name)
            arrival = random.randint(0, 50)
            # arrival = 5
            
            exec_time = random.randint(1, 3)
            deadline = random.randint(exec_time + 5, 20)
            
            # 極端情況
            # deadline = exec_time + 1
            
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
            exec_time = random.randint(1, 3)
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


def check_schedulable_EDF_DBF(tasks, t_max=None):
    """
    使用 EDF + Demand Bound Function 檢查 periodic task set 是否可排程
    假設：
      - 單核心
      - arrival_time = 0
      - 每個 task.deadline <= task.period (constrained / implicit deadline)
    tasks: list[PeriodicTask]
    t_max: 最大檢查時間 (若為 None，會根據 periods 推一個合理上界)
    """
    if not tasks:
        return True

    # 先做 quick check：utilization 必須 <= 1
    util = sum(t.exec_time / t.period for t in tasks)
    if util > 1.0 + 1e-9:
        return False

    periods = [t.period for t in tasks]
    deadlines = [t.deadline for t in tasks]

    # 設定檢查上界 t_max
    if t_max is None:
        # 粗略策略：
        #   - 取 periods 的 LCM（hyper-period），但避免太大
        #   - 再加上一點 buffer
        def lcm(a, b):
            return a * b // math.gcd(a, b)

        hyper = periods[0]
        for p in periods[1:]:
            hyper = lcm(hyper, p)

        # 限制不要太爆炸，對你現在 T<=25, n<=5 很安全
        t_max = min(hyper, 500)  # 500 是安全上限，可視情況調整

    # 產生所有「候選 t」：所有 k*T_i + D_i，在 (0, t_max] 範圍內
    candidate_ts = set()
    for tsk in tasks:
        C = tsk.exec_time
        T = tsk.period
        D = tsk.deadline

        # 從 k=0 開始往上疊
        k = 0
        while True:
            t = k * T + D
            if t <= 0:
                k += 1
                continue
            if t > t_max:
                break
            candidate_ts.add(t)
            k += 1

    # 沒有候選點就直接當作 ok（理論上不太會發生）
    if not candidate_ts:
        return True

    for t in sorted(candidate_ts):
        demand = 0
        for ti in tasks:
            Ci = ti.exec_time
            Ti = ti.period
            Di = ti.deadline

            if t < Di:
                continue
            # floor((t - Di) / Ti) + 1
            num_jobs = math.floor((t - Di) / Ti) + 1
            demand += num_jobs * Ci

        if demand > t:
            # 找到一個 t 使得 DBF(t) > t → 不可排程
            return False

    # 所有檢查的 t 都滿足 DBF(t) <= t → EDF 可排程
    return True
