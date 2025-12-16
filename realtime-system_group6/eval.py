import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class Metrics:
    def __init__(self, adv=False):
        self.drop_rate = 0.0
        self.h_miss_rate = 0.0
        self.s_miss_rate = 0.0
        self.avg_response_time = 0.0
        self.max_response_time = 0
        self.cpu_utilization = 0.0
        if adv:
            self.fairness = None
            self.jitter = None
            self.dependency_deadlock = None
            self.weighted_starvation = None

class Score:
    def __init__(self, task_model, scheduled_tasks,advance=False):
        self.task_model = task_model
        self.scheduled_tasks = scheduled_tasks
        self.advance = advance
        self.lantency = len(scheduled_tasks[list(scheduled_tasks.keys())[0]])
        self.metrics = {}
        self.preemptive = True if (('preemptive' in list(self.task_model['periodic'].values())[0].keys()) and ('preemptive' in list(self.task_model['sporadic'].values())[0].keys()) and ('preemptive' in list(self.task_model['aperiodic'].values())[0].keys())) else False
        self.priority = True if (('priority' in list(self.task_model['periodic'].values())[0].keys()) and ('priority' in list(self.task_model['sporadic'].values())[0].keys()) and ('priority' in list(self.task_model['aperiodic'].values())[0].keys())) else False
        self.dependencies = True if (('dependencies' in list(self.task_model['periodic'].values())[0].keys()) and ('dependencies' in list(self.task_model['sporadic'].values())[0].keys()) and ('dependencies' in list(self.task_model['aperiodic'].values())[0].keys())) else False

        for key in scheduled_tasks:
            self.metrics[key] = self.calculate_metrics(scheduled_tasks[key])

        global threshold
        threshold = {
            'hardMR': 0.0,
            'softMR': 0.11,
            'dropRate': 0.05,
            'avgRT': self.lantency / 10,
            'maxRT': self.lantency / 4,
            'cpuUtil': 0.7,
            'fairness': 0.7,
            'jitter': 15,
            'dependency_deadlock': False,
            'weighted_starvation': 4
        }

    def calculate_metrics(self, scheduled_tasks):
        result = Metrics(adv=self.advance)
        # drop rate
        # hard miss rate
        # soft miss rate
        # average response time
        # maximum response time 
        cnt = 0
        response_times = {}
        starvation = {}
        priorities = {}
        for ptask in self.task_model['periodic']:
            if self.priority:
                priorities[ptask] = self.task_model['periodic'][ptask]['priority']
            instances = (self.lantency - self.task_model['periodic'][ptask]['arrival_time'] + self.task_model['periodic'][ptask]['period'] - 1) // self.task_model['periodic'][ptask]['period']
            cnt += instances
            exec_time = self.task_model['periodic'][ptask]['execution_time']
            response_times[ptask] = 0.0
            for inst in range(instances):
                iter_at = self.task_model['periodic'][ptask]['arrival_time'] + inst * self.task_model['periodic'][ptask]['period']
                iter_dl = self.task_model['periodic'][ptask]['deadline'] + inst * self.task_model['periodic'][ptask]['period']
                exec_cnt = scheduled_tasks[iter_at:iter_dl+1].count(ptask)
                if exec_cnt == 0:
                    result.drop_rate += 1
                elif exec_cnt < exec_time:
                    result.h_miss_rate += 1
                else:
                    finish_time = max(i for i, x in enumerate(scheduled_tasks[iter_at:iter_dl+1]) if x == ptask) + 1 + iter_at
                    starvation[ptask] = starvation.get(ptask,0) + (finish_time - iter_at - exec_time)
                    if finish_time > iter_dl:
                        result.s_miss_rate += 1
                    else:
                        response_times[ptask] += finish_time - iter_at
            response_times[ptask] /= instances

        for stask in self.task_model['sporadic']:
            if self.priority:
                priorities[stask] = self.task_model['sporadic'][stask]['priority']
            cnt += 1
            if scheduled_tasks.count(stask) == 0:
                result.drop_rate += 1
            elif scheduled_tasks.count(stask) < self.task_model['sporadic'][stask]['execution_time']:
                result.h_miss_rate += 1
            else:
                finish_time = max(i for i, x in enumerate(scheduled_tasks) if x == stask) + 1
                starvation[stask] = starvation.get(stask, 0) + (finish_time - self.task_model['sporadic'][stask]['arrival_time'] - self.task_model['sporadic'][stask]['execution_time'])
                if finish_time > self.task_model['sporadic'][stask]['deadline']:
                    result.s_miss_rate += 1
                else:
                    response_times[stask] = finish_time - self.task_model['sporadic'][stask]['arrival_time']
        for atask in self.task_model['aperiodic']:
            if self.priority:
                priorities[atask] = self.task_model['aperiodic'][atask]['priority']
            cnt += 1
            if scheduled_tasks.count(atask) < self.task_model['aperiodic'][atask]['execution_time']:
                result.s_miss_rate += 1
            else:
                finish_time = max(i for i, x in enumerate(scheduled_tasks) if x == atask) + 1
                starvation[atask] = starvation.get(atask, 0) + (finish_time - self.task_model['aperiodic'][atask]['arrival_time'] - self.task_model['aperiodic'][atask]['execution_time'])
                if finish_time > self.task_model['aperiodic'][atask]['deadline']:
                    result.s_miss_rate += 1
                else:
                    response_times[atask] = finish_time - self.task_model['aperiodic'][atask]['arrival_time']
        result.drop_rate /= cnt
        result.h_miss_rate /= cnt
        result.s_miss_rate /= cnt
        if len(response_times) > 0:
            result.avg_response_time = sum(response_times.values()) / len(response_times)
            result.max_response_time = max(response_times.values())
        else:
            result.avg_response_time = 0.0
            result.max_response_time = 0
        # cpu utilization
        for i in range(self.lantency):
            if scheduled_tasks[i] != 'idle':
                result.cpu_utilization += 1.0
        result.cpu_utilization /= self.lantency

        if self.advance:
            # === Fairness ===
            usage = {}
            for slot in scheduled_tasks:
                if slot != "idle":
                    usage[slot] = usage.get(slot, 0) + 1
            x = np.array(list(usage.values()))
            result.fairness = ((x.sum()**2) / (len(x) * (x**2).sum()) if len(x) > 0 else 0)

            # === Jitter (based on response times) ===
            if len(response_times) > 1:
                result.jitter = np.std(list(response_times.values()), ddof=0)
            # === Deadlock detection (if dependencies exist) ===
            # 假設每個 task dict 內可能有 "dependencies": [list]
            # 這裡簡化直接檢查是否有循環依賴
            if self.dependencies:
                graph = {}
                for tcat in self.task_model.values():
                    for tid, t in tcat.items():
                        deps = t.get("dependencies", [])
                        graph[tid] = deps
                visited, stack = set(), set()
                def dfs(u):
                    if u in stack: return True
                    if u in visited: return False
                    visited.add(u); stack.add(u)
                    for v in graph.get(u, []):
                        if dfs(v): return True
                    stack.remove(u)
                    return False
                result.dependency_deadlock = any(dfs(node) for node in graph)

            # === Starvation check ===
            # 偵測長時間沒有執行的任務
            if self.priority:
                result.weighted_starvation = 0.0
                total_priority = 0
                for tid, priority in priorities.items():
                    total_priority += priority
                    if tid in starvation:
                        result.weighted_starvation += (starvation[tid] * priority)
                result.weighted_starvation /= total_priority if total_priority > 0 else None

        return result

    def get_performance(self,base_score=75):
        df = pd.DataFrame(columns=['Algorithm','Drop Rate','Hard Miss Rate','Soft Miss Rate','Avg Response Time','Max Response Time','CPU Utilization','Fairness','Jitter','Deadlock','Starvation','Score'])

        for algo in self.metrics:
            curr_score = base_score if self.algo_valid(algo) else 50
            if self.algo_valid(algo):
                curr_score -= 3 if self.metrics[algo].drop_rate > threshold['dropRate'] else 0
                curr_score -= 3 if self.metrics[algo].s_miss_rate > threshold['softMR'] else 0
                curr_score -= 2 if self.metrics[algo].avg_response_time > threshold['avgRT'] else 0
                curr_score -= 2 if self.metrics[algo].max_response_time > threshold['maxRT'] else 0
                curr_score -= 2 if self.metrics[algo].cpu_utilization < threshold['cpuUtil'] else 0 
                if self.advance:
                    curr_score += 1 if self.metrics[algo].fairness is not None and self.metrics[algo].fairness >= threshold['fairness'] else 0
                    curr_score += 1 if self.metrics[algo].jitter is not None and self.metrics[algo].jitter <= threshold['jitter'] else 0
                    curr_score += 1 if self.metrics[algo].dependency_deadlock is not None and self.metrics[algo].dependency_deadlock == threshold['dependency_deadlock'] else 0
                    curr_score += 1 if self.metrics[algo].weighted_starvation is not None and self.metrics[algo].weighted_starvation <= threshold['weighted_starvation'] else 0
            row = {
                'Algorithm': algo,
                'Drop Rate': f'{self.metrics[algo].drop_rate*100:2.1f} %',
                'Hard Miss Rate': f'{self.metrics[algo].h_miss_rate*100:2.1f} %',
                'Soft Miss Rate': f'{self.metrics[algo].s_miss_rate*100:2.1f} %',
                'Avg Response Time': f'{self.metrics[algo].avg_response_time:.1f}',
                'Max Response Time': self.metrics[algo].max_response_time,
                'CPU Utilization': f'{self.metrics[algo].cpu_utilization*100:2.1f} %',
                'Fairness': f'{self.metrics[algo].fairness*100:2.1f} %' if self.advance and self.metrics[algo].fairness is not None else 'N/A',
                'Jitter': f'{self.metrics[algo].jitter:.2f}' if self.advance and self.metrics[algo].jitter is not None else 'N/A',
                'Deadlock': self.metrics[algo].dependency_deadlock if self.advance and self.metrics[algo].dependency_deadlock is not None else 'N/A',
                'Starvation': f'{self.metrics[algo].weighted_starvation:.2f}' if self.advance and self.metrics[algo].weighted_starvation is not None else 'N/A',
                'Score': curr_score
            }
            df.loc[len(df)] = row
        print("========== Performance Summary ==========")
        final_score = 0

        # Advance of tasks
        final_score += 4 if self.preemptive else 0
        final_score += 3 if self.priority else 0
        final_score += 3 if self.dependencies else 0

        # Advance of algorithms
        advance_algos = 0
        for row in df.iterrows():
            if row[1]['Algorithm'] in ['EDF', 'FIFO', 'RM']:
                final_score += row[1]['Score'] / 3
            elif row[1]['Algorithm'] == 'myAlgo' and row[1]['Score'] >= base_score:
                final_score += 5
            elif advance_algos < 3 and row[1]['Score'] >= base_score:
                final_score += 2
                advance_algos += 1
        print(f"Final Score (including bonuses): {final_score:2.1f} %")
        return df.transpose()
    
    def algo_valid(self, algo):
        return algo in self.metrics and self.metrics[algo].h_miss_rate <= threshold['hardMR']

def plot_schedule(scheduled_tasks, title="Task Scheduling Results"):
    """Plot scheduling results for one type of tasks with fixed size and adaptive row height"""
    simulation_length = min(len(schedule) for schedule in scheduled_tasks.values())
    algorithms = list(scheduled_tasks.keys())
    num_algos = len(algorithms)
        
    # Create consistent color map for different task types
    all_tasks = set()
    for schedule in scheduled_tasks.values():
        all_tasks.update([task for task in schedule if task != 'idle'])
    
    def get_task_color(task_name):
        """Generate consistent colors based on task type and index"""
        if task_name.startswith('p') or task_name.startswith('P'):  # Periodic tasks - blue gradient
            task_num = int(task_name[1:]) if task_name[1:].isdigit() else 1
            # Light blue to dark blue
            blues = ['#E3F2FD', '#BBDEFB', '#90CAF9', '#64B5F6', '#42A5F5', '#2196F3', '#1E88E5', '#1976D2', '#1565C0', '#0D47A1']
            return blues[min(task_num - 1, len(blues) - 1)]
        elif task_name.startswith('s') or task_name.startswith('S'):  # Sporadic tasks - green gradient
            task_num = int(task_name[1:]) if task_name[1:].isdigit() else 1
            # Light green to dark green
            greens = ['#E8F5E8', '#C8E6C9', '#A5D6A7', '#81C784', '#66BB6A', '#4CAF50', '#43A047', '#388E3C', '#2E7D32', '#1B5E20']
            return greens[min(task_num - 1, len(greens) - 1)]
        elif task_name.startswith('a') or task_name.startswith('A'):  # Aperiodic tasks - red gradient
            task_num = int(task_name[1:]) if task_name[1:].isdigit() else 1
            # Light red to dark red
            reds = ['#FFEBEE', '#FFCDD2', '#EF9A9A', '#E57373', '#EF5350', '#F44336', '#E53935', '#D32F2F', '#C62828', '#B71C1C']
            return reds[min(task_num - 1, len(reds) - 1)]
        else:
            # Default colors for other task types
            return f"C{hash(task_name) % 10}"
    
    task_colors = {task: get_task_color(task) for task in sorted(all_tasks)}
        
    # Fixed figure size - height doesn't change with number of algorithms
    fig, ax = plt.subplots(figsize=(16, 4 + num_algos * 0.5))
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    # Calculate adaptive bar height and font size using ratio
    # Base values for 3 algorithms, scale proportionally
    base_algos = 3
    base_bar_height = 0.8
    base_font_size = 10
    
    # Scale inversely with number of algorithms
    bar_height = base_bar_height #* (base_algos / num_algos)
    font_size = max(8, int(base_font_size * (base_algos / num_algos)))  # Minimum font size of 6
        
    # Plot all algorithms in same coordinate system
    for algo_idx, (algo, schedule) in enumerate(scheduled_tasks.items()):
        y_position = algo_idx  # Each algorithm gets its own y-level
            
        # Plot each time slot as a bar
        for t, task_name in enumerate(schedule[:simulation_length]):
            if task_name != 'idle':
                ax.barh(y_position, 1, left=t, height=bar_height, 
                       color=task_colors[task_name], 
                       alpha=0.7, 
                       edgecolor='black', 
                       linewidth=0.5)
                ax.text(t + 0.5, y_position, task_name, 
                       fontsize=font_size, ha='center', va='center', 
                       fontweight='bold')
        
    ax.set_xlim(0, simulation_length)
    ax.set_ylim(-0.5, num_algos - 0.5)
    ax.set_yticks(range(num_algos))
    ax.set_yticklabels(algorithms, fontweight='bold')
    ax.set_xlabel("Time", fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
        
    # Create legend
    legend_elements = [plt.Rectangle((0,0),1,1, facecolor=task_colors[task], 
                                   alpha=0.7, edgecolor='black') 
                      for task in sorted(all_tasks)]
        
    # Position legend
    ax.legend(legend_elements, sorted(all_tasks), 
             title="Tasks", loc='center left', bbox_to_anchor=(1.02, 0.5))
        
    plt.tight_layout()
    plt.show()