import math

class EDFAcceptanceTest:
    def __init__(self, periodic_tasks, horizon_cap=200):
        """
        periodic_tasks: list of PeriodicTask
        horizon_cap: max window length to check
        """
        self.periodic_tasks = periodic_tasks
        self.horizon_cap = horizon_cap

    # ---------- Periodic offset-aware demand ----------
    def periodic_demand(self, now, window):
        demand = 0
        end = now + window

        for p in self.periodic_tasks:
            a, T, D, C = (
                p.arrival_time,
                p.period,
                p.deadline,
                p.exec_time
            )

            # absolute deadlines: a + kT + D
            base = a + D

            # first k s.t. deadline > now
            k_start = math.floor((now - base) / T) + 1
            if k_start < 0:
                k_start = 0

            # last k s.t. deadline <= end
            k_end = math.floor((end - base) / T)

            if k_end >= k_start:
                demand += (k_end - k_start + 1) * C

        return demand

    def sporadic_demand(self, sporadic_jobs, now, window):
        end = now + window
        return sum(
            j.remaining_time
            for j in sporadic_jobs
            if (not j.is_completed)
            and (j.absolute_deadline > now)
            and (j.absolute_deadline <= end)
        )
        
    def candidate_windows(self, sporadic_jobs, now):
        wins = set()

        # sporadic deadlines
        for j in sporadic_jobs:
            if j.absolute_deadline > now:
                w = j.absolute_deadline - now
                if w <= self.horizon_cap:
                    wins.add(w)

        # periodic deadlines
        for p in self.periodic_tasks:
            a, T, D = p.arrival_time, p.period, p.deadline
            base = a + D

            k = math.floor((now - base) / T) + 1
            if k < 0:
                k = 0

            while True:
                d = base + k * T
                if d > now + self.horizon_cap:
                    break
                if d > now:
                    wins.add(d - now)
                k += 1

        return sorted(wins)

    def accept(self, new_job, admitted_sporadic_jobs, now):
        """
        new_job: Job (sporadic, hard)
        admitted_sporadic_jobs: list of accepted hard sporadic jobs (may include current_job)
        """

        # active hard sporadic carry-in
        active = [
            j for j in admitted_sporadic_jobs
            if (not j.is_completed) and (j.absolute_deadline > now)
        ]

        cand_spor = active + [new_job]
        windows = self.candidate_windows(cand_spor, now)

        if not windows:
            return True  # nothing critical to check

        for w in windows:
            demand = 0
            demand += self.periodic_demand(now, w)
            demand += self.sporadic_demand(cand_spor, now, w)

            if demand > w:
                return False

        return True

