from task import PeriodicTask, SporadicTask, AperiodicTask
import random

class TaskSetGenerator:
    # 修改 1: 將預設 max_periodic_util 從 0.9 改為 0.75
    # 說明: RM 演算法的理論上限約為 0.69~0.77。設為 0.75 比較安全，EDF 則肯定沒問題。
    def __init__(self, use_preemption=False, use_priority=False, use_dependency=False, max_periodic_util=0.75):
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
            # 每次重試前，要過濾掉舊的 p 開頭任務名稱，以免重複累積
            self.all_task_names = [name for name in self.all_task_names if not name.startswith("p")]
            
            for i in range(1, n+1):
                name = f"p{i}"
                self.all_task_names.append(name)
                
                arrival = random.randint(0, 10)
                
                # 修改 2: 調整週期範圍與執行時間，避免單一任務負載過重
                exec_time = random.randint(1, 4)
                # 確保週期至少是執行時間的 2 倍以上，預留空隙
                period = random.randint(max(exec_time * 2, 10), 40)
                
                # 修改 3: 【關鍵】將 Deadline 設為等於 Period (Implicit Deadline)
                # 這是最容易保證 Hard Miss Rate = 0 的設定
                # 原本: deadline = random.randint(exec_time + 1, period)
                deadline = period 

                preemptive, priority, dep = self._add_optional_fields(self.all_task_names[:-1])
                t = PeriodicTask(name, arrival, exec_time, period, deadline, preemptive, priority, dep)
                tasks.append(t)
            
            # 檢查總利用率
            util = sum(t.exec_time / t.period for t in tasks)
            
            # 如果利用率在安全範圍內，且不為 0，則跳出迴圈
            if util <= self.max_periodic_util and util > 0:
                break
            
            # 如果嘗試太多次都失敗(通常是因為隨機數很難湊到剛好的 utilization)，
            # 強制接受但印個警告，或是這邊通常利用率會設寬鬆點所以容易過
            if attempts > 200:
                print(f"Warning: Could not generate task set under utilization {self.max_periodic_util} after 200 attempts. Current Util: {util:.2f}")
                break
                
        return tasks

    def generate_sporadic(self, n):
        tasks = []
        for i in range(1, n+1):
            name = f"s{i}"
            self.all_task_names.append(name)
            arrival = random.randint(0, 50)
            exec_time = random.randint(1, 3) # 稍微調小執行時間，減少對 Periodic 的干擾
            
            # 給予較寬鬆的 Deadline
            deadline = random.randint(exec_time + 10, 30)
            interval = random.randint(10, 20)
            
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
            exec_time = random.randint(1, 3) # 稍微調小執行時間
            
            # 給予較寬鬆的 Deadline
            deadline = random.randint(exec_time + 15, 40)
            
            preemptive, priority, dep = self._add_optional_fields(self.all_task_names[:-1])
            t = AperiodicTask(name, arrival, exec_time, deadline, preemptive, priority, dep)
            tasks.append(t)
        return tasks

    def generate_task_set(self, np=3, ns=2, na=2):
        # 這裡會清空名稱列表，確保每次生成都是全新的
        self.all_task_names = []
        periodic = self.generate_periodic(np)
        sporadic = self.generate_sporadic(ns)
        aperiodic = self.generate_aperiodic(na)
        return periodic + sporadic + aperiodic