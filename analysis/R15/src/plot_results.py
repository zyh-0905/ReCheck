"""Optional figure only. Requires matplotlib; analysis reproduction does not."""
from pathlib import Path
import csv
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
with (root / 'results/reproduced/by_task.csv').open(encoding='utf-8', newline='') as f:
    rows = list(csv.DictReader(f))[:3]
full = [int(r['source_full']) for r in rows]
conflict = [int(r['conservative_conflicts']) for r in rows]
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.bar([i-.18 for i in range(3)], full, width=.36, label='Source progress = 1')
ax.bar([i+.18 for i in range(3)], conflict, width=.36, label='Full-score / effect conflicts')
ax.set_xticks(range(3), ['Specified date', 'Tomorrow', 'Next Friday'])
ax.set_ylabel('Recorded episodes'); ax.set_ylim(0, 100)
ax.set_title('Reminder tasks: 96 public records per task')
ax.legend(loc='upper center', bbox_to_anchor=(.5, 1), ncol=2, fontsize=9)
for i, (f, c) in enumerate(zip(full, conflict)):
    ax.text(i-.18, f+1, str(f), ha='center', fontsize=10)
    ax.text(i+.18, c+1, str(c), ha='center', fontsize=10)
fig.text(.5, .015, 'Retrospective subset audit; repeated task templates, not a benchmark-wide error rate.', ha='center', fontsize=8)
fig.tight_layout(rect=(0, .045, 1, 1))
(root/'figures').mkdir(exist_ok=True)
fig.savefig(root/'figures/reminder_effect_conflicts.png', dpi=200)
fig.savefig(root/'figures/reminder_effect_conflicts.svg')
plt.close(fig)
