import math
import random
from task import *
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class _PJob:
    task_name: str
    remaining: int
    abs_deadline: int
    release: int

class PeriodicSlackProfiler:
    """
    用 periodic-only 的 preemptive EDF 模擬，找出 [0, horizon) 的 slack intervals。
    支援 periodic arrival_time != 0
    """

    def __init__(self, periodic_tasks):
        self.periodic_tasks = periodic_tasks

    def _release_periodic_jobs(self, t: int) -> List[_PJob]:
        jobs = []
        for p in self.periodic_tasks:
            a, T, C, D = p.arrival_time, p.period, p.exec_time, p.deadline
            if t >= a and (t - a) % T == 0:
                jobs.append(_PJob(
                    task_name=p.name,
                    remaining=C,
                    abs_deadline=t + D,
                    release=t
                ))
        return jobs

    def build_timeline_and_slack(self, horizon: int) -> Tuple[List[str], List[Tuple[int, int]]]:
        ready: List[_PJob] = []
        timeline: List[str] = []

        for t in range(horizon):
            # release periodic jobs
            ready.extend(self._release_periodic_jobs(t))

            # pick EDF among periodic
            ready = [j for j in ready if j.remaining > 0]
            if ready:
                ready.sort(key=lambda j: (j.abs_deadline, j.release))
                cur = ready[0]
                cur.remaining -= 1
                timeline.append(cur.task_name)
            else:
                timeline.append("IDLE")

        # extract slack intervals
        slack: List[Tuple[int, int]] = []
        i = 0
        while i < horizon:
            if timeline[i] != "IDLE":
                i += 1
                continue
            start = i
            while i < horizon and timeline[i] == "IDLE":
                i += 1
            end = i
            slack.append((start, end))  # [start, end)
        return timeline, slack



class SlackBasedSporadicGenerator:
    """
    只在 slack intervals 裡面生成 sporadic task：
    - arrival_time 落在 slack 內
    - exec_time <= slack_len
    - relative deadline = slack_end - arrival_time (確保可以在 slack 結束前完成)
    """

    def __init__(self, *, min_exec=1, max_exec=3, safety_margin=0, seed=None):
        self.min_exec = min_exec
        self.max_exec = max_exec
        self.safety_margin = safety_margin
        if seed is not None:
            random.seed(seed)

    def generate(self, ns: int, slack_intervals: List[Tuple[int, int]], start_idx=1):
        sporadic_tasks = []
        sid = start_idx

        # 複製一份 slack，並用「消耗式塞入」避免超量
        slack = [(s, e) for (s, e) in slack_intervals]

        for (s, e) in slack:
            if len(sporadic_tasks) >= ns:
                break

            cur = s
            while cur < e and len(sporadic_tasks) < ns:
                slack_len = e - cur
                if slack_len < self.min_exec:
                    break

                C = random.randint(self.min_exec, min(self.max_exec, slack_len))
                arrival = cur  # 直接貼齊 slack 起點，最穩（也可以 random 在 [cur, e-C]）
                latest_finish = e - self.safety_margin

                # 必須能完成
                if arrival + C > latest_finish:
                    break

                rel_deadline = latest_finish - arrival  # relative deadline
                name = f"s{sid}"
                sid += 1

                # 你原本 SporadicTask 需要 (name, arrival, exec, deadline, interval, preemptive, priority, deps)
                # interval/min_interval 在 slack-only 模式其實可忽略，這裡給個合理值
                interval = max(5, C + 1)

                # 重要：加上 slack_only=True（你要在 SporadicTask 類別中加這個欄位，或用 setattr）
                t = SporadicTask(
                    name,
                    arrival,
                    C,
                    rel_deadline,
                    interval,
                    True,   # preemptive
                    None,   # priority (可選)
                    []      # dependencies
                )
                setattr(t, "is_hard", True)
                setattr(t, "slack_only", True)

                sporadic_tasks.append(t)

                # 消耗 slack：下一個 job 從 cur+C 開始塞
                cur += C

        return sporadic_tasks
