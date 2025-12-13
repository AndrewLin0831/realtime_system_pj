# schedulers.py
from task import PeriodicTask, Job
import statistics

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
                new_jobs.append(Job(task, time, abs_deadline))
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

    def evaluate(self, completed_jobs, total_released_count, sim_time, all_released_jobs):
        """計算詳細效能指標"""
        
        # 1. 基礎計數
        completed_set = set(j.name for j in completed_jobs)
        dropped_jobs = [j for j in all_released_jobs if j.name not in completed_set]
        
        miss_count = sum(1 for j in completed_jobs if j.is_missed)
        dropped_count = len(dropped_jobs)

        # 2. 分類 Hard (Periodic) vs Soft (Others)
        # 假設 Periodic Task 為 Hard Real-time
        hard_jobs = [j for j in all_released_jobs if isinstance(j.task, PeriodicTask)]
        soft_jobs = [j for j in all_released_jobs if not isinstance(j.task, PeriodicTask)]
        
        total_hard = len(hard_jobs)
        total_soft = len(soft_jobs)

        # Hard Miss = Completed but Late + Dropped
        hard_missed_completed = sum(1 for j in completed_jobs if j.is_missed and isinstance(j.task, PeriodicTask))
        hard_dropped = sum(1 for j in dropped_jobs if isinstance(j.task, PeriodicTask))
        total_hard_miss = hard_missed_completed + hard_dropped
        
        # Soft Miss
        soft_missed_completed = sum(1 for j in completed_jobs if j.is_missed and not isinstance(j.task, PeriodicTask))
        soft_dropped = sum(1 for j in dropped_jobs if not isinstance(j.task, PeriodicTask))
        total_soft_miss = soft_missed_completed + soft_dropped

        hard_miss_rate = (total_hard_miss / total_hard) if total_hard > 0 else 0.0
        soft_miss_rate = (total_soft_miss / total_soft) if total_soft > 0 else 0.0

        # 3. Response Time & Jitter
        response_times = [j.finish_time - j.release_time for j in completed_jobs]
        avg_resp = statistics.mean(response_times) if response_times else 0
        max_resp = max(response_times) if response_times else 0
        
        # Jitter: Response Time 的標準差
        overall_jitter = statistics.pstdev(response_times) if len(response_times) > 1 else 0

        # 4. Fairness (Jain's Fairness Index 概念，或使用 CPU time 標準差)
        # 這裡計算 CPU share 的標準差，越低越公平
        total_busy = sum(j.task.exec_time for j in completed_jobs)
        cpu_util = (total_busy / sim_time) if sim_time else 0
        
        # 計算每個 Task 獲得的 CPU 時間
        task_cpu_map = {}
        for j in completed_jobs:
            task_cpu_map[j.task.name] = task_cpu_map.get(j.task.name, 0) + j.task.exec_time
        
        if task_cpu_map:
            cpu_values = list(task_cpu_map.values())
            # Fairness 簡單定義：1 - (CPU 分配的變異係數)
            fairness = 1.0 - (statistics.pstdev(cpu_values) / statistics.mean(cpu_values)) if statistics.mean(cpu_values) > 0 else 0
        else:
            fairness = 0

        # 5. Dependency Deadlock Rate (檢查是否有 Job 因為相依性一直沒被執行)
        # 簡單定義：如果 Dropped Job 中有是因為相依性卡住的
        dep_deadlock = 0.0 # 實作複雜，暫時設 0，除非偵測到循環

        # 6. Priority Starvation
        # 檢查是否有高優先權任務一直搶佔低優先權
        starvation_score = 0.0 # 暫留

        return {
            "Algorithm": self.name,
            "Drop Rate": f"{(dropped_count/total_released_count):.2%}" if total_released_count else "0%",
            "Hard Miss Rate": f"{hard_miss_rate:.2%}",
            "Soft Miss Rate": f"{soft_miss_rate:.2%}",
            "Avg Resp Time": f"{avg_resp:.2f}",
            "Max Resp Time": max_resp,
            "Overall Jitter": f"{overall_jitter:.3f}",
            "CPU Util": f"{cpu_util:.2%}",
            "Completed": len(completed_jobs),
            "Dropped": dropped_count,
            "Fairness": f"{fairness:.3f}",
            "Dependency Deadlock": dep_deadlock,
            "Priority-Starvation": f"{starvation_score:.3f}"
        }

    def run(self, tasks, sim_time=100):
        current_time = 0
        ready_queue = []
        completed_jobs = []
        all_released_jobs = [] # 追蹤所有產生的 Job
        
        current_job = None
        timeline = []
        released_flags = {}

        for t in range(sim_time):
            current_time = t

            # 1. 釋放新工作
            new_jobs = self._release_jobs(t, tasks, released_flags)
            ready_queue.extend(new_jobs)
            hard_new_arrived = any(getattr(j.task, "is_hard", False) for j in new_jobs)

            # 若剛有硬即時工作到達，強制中斷當前非-hard 工作（不論 scheduler.preemptive）
            if hard_new_arrived and current_job and not getattr(current_job.task, "is_hard", False) and not current_job.is_completed:
                ready_queue.append(current_job)
                current_job = None
                
            # 2. 處理 Preemption (搶佔)
            needs_reschedule = (
                self.preemptive or 
                current_job is None or 
                current_job.is_completed
            )

            if needs_reschedule:
                # 如果當前工作還沒做完就被搶佔，放回 Queue
                if current_job and not current_job.is_completed:
                    ready_queue.append(current_job)
                    current_job = None
                
                # 3. 篩選依賴滿足的 Jobs (Dependency Check)
                eligible_jobs = [j for j in ready_queue if self._eligible(j, completed_jobs)]
                
                if eligible_jobs:
                    # 4. 演算法挑選 Job
                    picked = self.pick_job(eligible_jobs, current_time)
                    if picked:
                        current_job = picked
                        # 從 ready_queue 移除 (注意：pick_job 回傳的是物件引用)
                        if current_job in ready_queue:
                            ready_queue.remove(current_job)

            # 5. 執行
            if current_job:
                if current_job.start_time == -1:
                    current_job.start_time = t
                current_job.remaining_time -= 1
                timeline.append((t, current_job.name))

                if current_job.remaining_time <= 0:
                    current_job.finish_time = t + 1
                    current_job.is_completed = True
                    # 檢查是否 Miss
                    if current_job.finish_time > current_job.absolute_deadline:
                        current_job.is_missed = True
                    
                    completed_jobs.append(current_job)
                    current_job = None
            else:
                timeline.append((t, "IDLE"))

        metrics = self.evaluate(completed_jobs, len(all_released_jobs), sim_time, all_released_jobs)
        return {
            "timeline": timeline,
            "metrics": metrics
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
        return sorted(queue, key=lambda j: j.release_time)[0]


class EDFScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "EDF"
        self.preemptive = True 

    def pick_job(self, queue, current_time):
        # 依照 Absolute Deadline 排序
        if not queue: return None
        return sorted(queue, key=lambda j: j.absolute_deadline)[0]


class RMScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "RM"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # 依照 Period 排序 (週期越短，優先權越高)
        if not queue: return None
        def get_period(job):
            if isinstance(job.task, PeriodicTask):
                return job.task.period
            return 9999999 # 非週期任務優先權最低
        return sorted(queue, key=get_period)[0]


class LLFScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "LLF"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # Least Laxity First
        # Laxity = (AbsDeadline - CurrentTime) - RemainingTime
        if not queue: return None
        return sorted(queue, key=lambda j: (j.absolute_deadline - current_time) - j.remaining_time)[0]


class DMScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "DM" # Deadline Monotonic
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # 依照 Relative Deadline 排序 (D 越短優先權越高)
        if not queue: return None
        return sorted(queue, key=lambda j: j.task.deadline)[0]


class PriorityInheritanceScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "PriorityInheritance"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # 依照 Priority 排序 (數字越小優先權越高，假設 1 最高)
        if not queue: return None
        # 若 Priority 未定義，給予最大值 (最低優)
        return sorted(queue, key=lambda j: getattr(j.task, 'priority', 9999))[0]


# SJF as independent scheduler
class SJFScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "SJF"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # Shortest Job First: 剩餘執行時間最短的先做
        if not queue: return None
        return sorted(queue, key=lambda j: j.remaining_time)[0]


# MyAlgo: example hybrid (deadline then short job)
class MyAlgoScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.name = "myAlgo"
        self.preemptive = True

    def pick_job(self, queue, current_time):
        # primary: earliest absolute deadline, tie-break: smallest remaining time
        if not queue: return None
        return sorted(queue, key=lambda j: (j.absolute_deadline, j.remaining_time))[0]