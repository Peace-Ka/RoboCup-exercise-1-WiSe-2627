"""I export the measured movement comparison for the presentation.

Optional plotting dependency: matplotlib. The controller does not depend on it.
Run from the repository root: python scripts/plot_movement.py
"""

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results/movement'
rows = list(csv.DictReader((RESULTS / 'trajectory.csv').open(encoding='utf-8')))
summary = json.loads((RESULTS / 'summary.json').read_text(encoding='utf-8'))
fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
colors = {'before': '#b45309', 'after': '#0369a1'}
labels = {'before': 'Before: supplied circular motion', 'after': 'After: my movement controller'}
for mode in ['before', 'after']:
    data = [r for r in rows if r['scenario'] == 'diagonal' and r['mode'] == mode]
    x, y, t = [[float(r[key]) for r in data] for key in ['x_m', 'y_m', 'time_s']]
    axes[0, 0].plot(x, y, color=colors[mode], label=labels[mode], linewidth=2)
    axes[0, 0].scatter(x[-1], y[-1], color=colors[mode], s=35)
    axes[0, 1].plot(t, [float(r['distance_m']) for r in data], color=colors[mode], label=labels[mode])
    axes[1, 0].plot(t, [abs(float(r['heading_error_deg'])) for r in data], color=colors[mode])
axes[0, 0].scatter([-1], [-0.6], marker='o', color='black', label='Same start')
axes[0, 0].scatter([0.7], [0.6], marker='*', s=180, color='#15803d', label='Target')
axes[0, 0].add_patch(plt.Circle((0.7, 0.6), 0.05, fill=False, color='#15803d'))
axes[0, 0].set(xlabel='Field x (m)', ylabel='Field y (m)', title='Diagonal trial: measured robot paths')
axes[0, 0].axis('equal')
axes[0, 0].legend(fontsize=8)
axes[0, 1].axhline(0.05, color='#15803d', linestyle='--', label='5 cm tolerance')
axes[0, 1].set(xlabel='Simulation time (s)', ylabel='Distance to target (m)', title='Position convergence')
axes[0, 1].legend(fontsize=8)
axes[1, 0].axhline(3, color='#15803d', linestyle='--')
axes[1, 0].set(xlabel='Simulation time (s)', ylabel='Absolute heading error (degrees)', title='Heading convergence (3 degree tolerance)')
after = [s for s in summary if s['mode'] == 'after']
axes[1, 1].barh([s['scenario'] for s in after], [s['final_distance_m'] * 100 for s in after], color='#0369a1')
axes[1, 1].axvline(5, color='#15803d', linestyle='--', label='5 cm tolerance')
axes[1, 1].set(xlabel='Final position error (cm)', title='All six controller scenarios (8 seconds each)')
axes[1, 1].legend(fontsize=8)
for ax in axes.flat:
    ax.grid(alpha=0.2)
fig.suptitle('Member 1: movement before and after in rSoccer', fontsize=16)
fig.savefig(RESULTS / 'comparison.png', dpi=160)
fig.savefig(RESULTS / 'comparison.svg')
print(RESULTS / 'comparison.png')
