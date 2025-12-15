# schedulers.py
from task import *
from EDFAcceptanceTest import EDFAcceptanceTest
import statistics
import math

class BaseScheduler:
    def __init__(self):
        self.name = "Base"
        self.preemptive = False

    def _release_jobs(self, time, tasks, released_flags):
        """釋放到達的任務成為 Job"""
        new_jobs = []
        for task in tasks:
            should_release = False
            if isinstance(task, PeriodicTask):
                # 週期性任務
                if time >= task.arrival_time and (time - task.arrival_time) % task.period == 0:
                    should_release = True
            else:
                # 偶發/非週期性任務 (簡化為一次性釋放)
                if not released_flags.get(task.name, False) and time == task.arrival_time:
                    should_release = True
                    released_flags[task.name] = True
            
            if should_release:
                # 計算絕對截止時間
                abs_deadline = time + task.deadline
                priority = task.priority if task.priority is not None else float('inf')
                preemptive = task.preemptive
                new_jobs.append(Job(task, time, abs_deadline, priority, preemptive))
        return new_jobs

    def _eligible(self, job, completed_jobs):
        """檢查依賴性：所有依賴的任務必須曾經完成過"""
        # 取得任務的相依列表，容錯處理屬性名稱
        deps = getattr(job.task, "dependencies", []) or getattr(job.task, "dependency", []) or []
        if not deps:
            return True
        
        # 取得已完成任務的名稱集合
        completed_names = {j.task.name for j in completed_jobs}
        
        # 檢查是否所有依賴都已存在於已完成名單中
        return all(d in completed_names for d in deps)

    def pick_job(self, queue, current_time):
        """子類別必須實作：從 Ready Queue 挑選一個 Job"""
        raise NotImplementedError("必須在子類別實作此方法")
    
    def is_hard(task):
        """判定 deadline 屬性"""
        return isinstance(task, (PeriodicTask, SporadicTask))
    
    def accept_job(self, job, ready_queue, current_job, time) -> bool:
        """
        檢查是否接受此 job（Hard Real-Time acceptance test）
        回傳 True / False
        """
        raise NotImplementedError

    def evaluate(self, completed_jobs, total_released_count, sim_time, all_released_jobs):
        """計算詳細效能指標（Hard miss 僅依 is_missed 判斷）"""

        # -------------------------------------------------
        # 1. 基礎集合
        # -------------------------------------------------
        completed_set = set(j for j in completed_jobs)

        # 注意：dropped 只是「未完成」，不是 miss
        dropped_jobs = [
            j for j in all_released_jobs
            if j not in completed_set
        ]

        # -------------------------------------------------
        # 2. Hard / Soft 分類
        # -------------------------------------------------
        hard_jobs = [j for j in all_released_jobs if j.task.is_hard]
        soft_jobs = [j for j in all_released_jobs if not j.task.is_hard]

        # -------------------------------------------------
        # 3. Hard Miss（唯一正確來源：j.is_missed）
        # -------------------------------------------------
        hard_miss = sum(1 for j in hard_jobs if (j.is_missed))
        hard_miss_rate = hard_miss / len(hard_jobs) if hard_jobs else 0.0
        
        hard_miss_jobs = [j.name for j in hard_jobs if j.is_missed]
        print(f"[DEBUG] Hard Miss Job: {hard_miss_jobs}")

        # -------------------------------------------------
        # 4. Soft Miss（允許 miss，但仍統計）
        # -------------------------------------------------
        soft_miss = sum(1 for j in soft_jobs if j.is_missed)
        soft_miss_rate = soft_miss / len(soft_jobs) if soft_jobs else 0.0

        # -------------------------------------------------
        # 5. Response Time & Jitter（僅完成的）
        # -------------------------------------------------
        response_times = [
            j.finish_time - j.release_time
            for j in completed_jobs
            if j.finish_time is not None
        ]

        avg_resp = statistics.mean(response_times) if response_times else 0
        max_resp = max(response_times) if response_times else 0
        overall_jitter = statistics.pstdev(response_times) if len(response_times) > 1 else 0

        # -------------------------------------------------
        # 6. CPU Utilization
        # -------------------------------------------------
        total_busy = sum(j.task.exec_time for j in completed_jobs)
        cpu_util = (total_busy / sim_time) if sim_time else 0

        # -------------------------------------------------
        # 7. Fairness（task-level）
        # -------------------------------------------------
        task_cpu_map = {}
        for j in completed_jobs:
            task_cpu_map[j.task.name] = task_cpu_map.get(j.task.name, 0) + j.task.exec_time

        if task_cpu_map and statistics.mean(task_cpu_map.values()) > 0:
            fairness = 1.0 - (
                statistics.pstdev(task_cpu_map.values())
                / statistics.mean(task_cpu_map.values())
            )
        else:
            fairness = 0.0

        # -------------------------------------------------
        # 8. 回傳結果
        # -------------------------------------------------
        return {
            "Algorithm": self.name,
            "Drop Rate": f"{(len(dropped_jobs)/total_released_count):.2%}" if total_released_count else "0%",
            "Hard Miss Rate": f"{hard_miss_rate:.2%}",
            "Soft Miss Rate": f"{soft_miss_rate:.2%}",
            "Avg Resp Time": f"{avg_resp:.2f}",
            "Max Resp Time": max_resp,
            "Overall Jitter": f"{overall_jitter:.3f}",
            "CPU Util": f"{cpu_util:.2%}",
            "Completed": len(completed_jobs),
            "Dropped": len(dropped_jobs),
            "Fairness": f"{fairness:.3f}",
            "Dependency Deadlock": 0.0,
            "Priority-Starvation": "0.000"
        }


    def run(self, tasks, sim_time=100):
        current_time = 0
        ready_queue = []
        completed_jobs = []
        all_released_jobs = []
        dropped_jobs = []

        current_job = None
        timeline = []
        released_flags = {}
        periodic_tasks = [t for t in tasks if isinstance(t, PeriodicTask)]
        
        self.admission = EDFAcceptanceTest(
            periodic_tasks=periodic_tasks,
            horizon_cap=sim_time
        )

        for t in range(sim_time):
            current_time = t

            # ---------------------------------------
            # 1. 釋放新工作
            # ---------------------------------------
            new_jobs = self._release_jobs(t, tasks, released_flags)

            # acceptive test
            for j in new_jobs:
                if j.task.is_hard and isinstance(j.task, SporadicTask):
                    ok = self.admission.accept(
                        new_job=j,
                        admitted_sporadic_jobs=[x for x in ready_queue if isinstance(x.task, SporadicTask) and x.task.is_hard] + ([current_job] if current_job else []),
                        now=t
                    )
                    if ok:
                        ready_queue.append(j)
                        all_released_jobs.append(j)
                    else:
                        # 拒絕：算 drop（hard drop）
                        j.is_missed = True
                        dropped_jobs.append(j)
                        all_released_jobs.append(j)  # 仍記錄，用來計 drop rate
                else:
                    # periodic hard 一定收；aperiodic soft 直接收
                    ready_queue.append(j)
                    all_released_jobs.append(j)


            # ---------------------------------------
            # 2. Preemption or scheduling point
            # ---------------------------------------
            needs_reschedule = False

            hard_arrived = any(j.task.is_hard for j in new_jobs)

            # Case 1: current job finished or CPU idle
            if current_job is None or current_job.is_completed:
                needs_reschedule = True

            else:
                # Case 2: hard job arrived -> must preempt soft (hard overrides soft)
                if hard_arrived and (not current_job.task.is_hard):
                    needs_reschedule = True

                # Case 3: normal preemptive scheduling within same class (hard-hard or soft-soft)
                elif self.preemptive and new_jobs:
                    # 用 eligible 的 top 來比較，避免 dependency 未滿足的 job 造成誤判
                    eligible_now = [j for j in ready_queue if self._eligible(j, completed_jobs)]
                    top = self.pick_job(eligible_now, current_time) if eligible_now else None

                    # 如果 top 不是 current_job 且 current_job 允許被搶佔 → 搶佔
                    #（你也可以把 current_job.preemptive 的限制拿掉，讓 preemptive scheduler 一律可搶佔）
                    if top and top is not current_job and getattr(current_job, "preemptive", True):
                        needs_reschedule = True


            # ---------------------------------------
            # 進行重新排程（若需要）
            # ---------------------------------------
            if needs_reschedule:

                # 先把 current_job 放回 ready queue（除非已完成）
                if current_job and not current_job.is_completed:
                    ready_queue.append(current_job)

                # 選新 job
                '''
                eligible = [j for j in ready_queue if self._eligible(j, completed_jobs)]
                new_job = self.pick_job(eligible, current_time) if eligible else None
                '''
                
                hard_jobs = [j for j in ready_queue if j.task.is_hard and self._eligible(j, completed_jobs)]
                soft_jobs = [j for j in ready_queue if not j.task.is_hard and self._eligible(j, completed_jobs)]

                if hard_jobs:
                    new_job = self.pick_job(hard_jobs, current_time)
                elif soft_jobs:
                    new_job = self.pick_job(soft_jobs, current_time)
                else:
                    new_job = None


                if new_job:
                    current_job = new_job
                    ready_queue.remove(new_job)
                else:
                    current_job = None

            # ---------------------------------------
            # 3. 執行 current_job
            # ---------------------------------------
            if current_job:
                if current_job.start_time == -1:
                    current_job.start_time = t

                current_job.remaining_time -= 1
                current_job.run_time += 1  # 用來計算 CPU utilization
                timeline.append((t, current_job.name))

                # 任務完成
                if current_job.remaining_time <= 0:
                    current_job.finish_time = t + 1
                    current_job.is_completed = True
                    current_job.is_missed = (current_job.finish_time > current_job.absolute_deadline)

                    completed_jobs.append(current_job)
                    current_job = None

            else:
                # CPU idle
                timeline.append((t, "IDLE"))

        # ===================================================
        # 4. 模擬結束後，處理未完成但已釋放的 job → dropped job
        # ===================================================
                    
        completed_ids = {id(j) for j in completed_jobs}
        for job in all_released_jobs:
            if id(job) not in completed_ids:
                job.is_completed = False
                job.finish_time = None
                if job.absolute_deadline <= sim_time:
                    job.is_missed = True
                    dropped_jobs.append(job)
              
        '''      
        print("released =", len(all_released_jobs))
        print("completed =", len(completed_jobs))
        print("dropped =", len(dropped_jobs))

        if dropped_jobs:
            j = dropped_jobs[0]
            print("Dropped job:", j.name, "release=", j.release_time, "absD=", j.absolute_deadline,
                "remaining=", j.remaining_time, "start=", j.start_time, "finish=", j.finish_time)
        '''

        # ===================================================
        # 5. 回傳統計
        # ===================================================
        metrics = self.evaluate(
            completed_jobs,
            len(all_released_jobs),
            sim_time,
            all_released_jobs
        )

        return {
            "timeline": timeline,
            "metrics": metrics,
            "all_released_jobs": all_released_jobs,
            "completed_jobs": completed_jobs,
            "dropped_jobs": dropped_jobs
        }



# ==========================================
# 各種具體的演算法實作
# ==========================================

class FIFOScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "FIFO"
        self.preemptive = False # FIFO 通常不可搶佔

    def pick_job(self, queue, current_time):
        # 依照 Release Time 排序 (先來的先做)
        if not queue: return None
        return sorted(queue, key=lambda j: (j.release_time, j.priority))[0]
    
    def accept_job(self, job, ready_queue, current_job, time):
        # FIFO 通常不能保證 hard-RT
        # 最簡單版本：只檢查 job 自己能否趕上 deadline
        return time + job.remaining_time <= job.absolute_deadline


class EDFScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "EDF"
        self.preemptive = True 

    def pick_job(self, queue, current_time):
        # 依照 Absolute Deadline 排序
        if not queue: return None
        return sorted(queue, key=lambda j: (j.absolute_deadline, j.priority))[0]
    
    def accept_job(self, job, ready_queue, current_job, time):
        # EDF demand-based acceptance test:
        # 所有 job 的需求不能大於時間窗長度

        window = job.absolute_deadline - time
        demand = job.remaining_time + sum(j.remaining_time for j in ready_queue)

        return demand <= window


class RMScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "RM"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # 依照 Period 排序 (週期越短，優先權越高)
        if not queue: return None
        def sort_key(job):
            # 是否為 periodic（False < True）
            is_aperiodic = not isinstance(job.task, PeriodicTask)

            # Period（非週期任務給極大值）
            period = job.task.period if not is_aperiodic else float('inf')

            # Release time
            release_time = job.release_time

            # Priority（數字越小越高）
            priority = job.priority

            return (is_aperiodic, period, release_time, priority)

        return min(queue, key=sort_key)
    
    def accept_job(self, job, ready_queue, current_job, time):

        # 把所有 higher priority 的任務取出
        hp_tasks = [j for j in ready_queue if j.task.period < job.task.period]

        # 進行 Response Time Analysis
        Ci = job.remaining_time
        Di = job.task.deadline
        Ri = Ci

        while True:
            interference = sum(
                math.ceil(Ri / hp_j.task.period) * hp_j.task.exec_time
                for hp_j in hp_tasks
            )
            new_Ri = Ci + interference
            if new_Ri == Ri:
                break
            Ri = new_Ri
            if Ri > Di:
                return False
        
        return True


class LLFScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "LLF"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # Least Laxity First
        # Laxity = (AbsDeadline - CurrentTime) - RemainingTime
        if not queue: return None
        return sorted(queue, key=lambda j: (((j.absolute_deadline - current_time) - j.remaining_time) , j.priority))[0]
    
    def accept_job(self, job, ready_queue, current_job, time):
        window = job.absolute_deadline - time
        demand = job.remaining_time + sum(j.remaining_time for j in ready_queue)
        return demand <= window



class DMScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "DM" # Deadline Monotonic
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # 依照 Relative Deadline 排序 (D 越短優先權越高)
        if not queue: return None
        return sorted(queue, key=lambda j: (j.task.deadline, j.priority))[0]
    
    def accept_job(self, job, ready_queue, current_job, time):

        # 把所有 higher priority 的任務取出
        hp_tasks = [j for j in ready_queue if j.task.deadline < job.task.deadline]

        # 進行 Response Time Analysis
        Ci = job.remaining_time
        Di = job.task.deadline
        Ri = Ci

        while True:
            interference = sum(
                math.ceil(Ri / hp_j.task.period) * hp_j.task.exec_time
                for hp_j in hp_tasks
            )
            new_Ri = Ci + interference
            if new_Ri == Ri:
                break
            Ri = new_Ri
            if Ri > Di:
                return False
        
        return True


class PriorityInheritanceScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "PriorityInheritance"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # 依照 Priority 排序 (數字越小優先權越高，假設 1 最高)
        if not queue: return None
        # 若 Priority 未定義，給予最大值 (最低優)
        return sorted(queue, key=lambda j: j.priority)[0]


# SJF as independent scheduler
class SJFScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "SJF"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # Shortest Job First: 剩餘執行時間最短的先做
        if not queue: return None
        return sorted(queue, key=lambda j: (j.remaining_time, j.priority))[0]


# MyAlgo: example hybrid (deadline then short job)
class MyAlgoScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "myAlgo"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # primary: earliest absolute deadline, tie-break: smallest remaining time
        if not queue: return None
        return sorted(queue, key=lambda j: (j.absolute_deadline, j.remaining_time, j.priority))[0]
    
    def accept_job(self, job, ready_queue, current_job, time):

        # EDF demand-based acceptance test
        window = job.absolute_deadline - time

        # 所有 ready job 的剩餘執行時間 + 新 job 的執行時間
        demand = job.remaining_time + sum(j.remaining_time for j in ready_queue)

        return demand <= window
    