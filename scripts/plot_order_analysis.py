#!/usr/bin/env python3
"""
Plot order quality analysis: invalid rates and complexity comparison
"""

import json
import matplotlib.pyplot as plt
import numpy as np

# Load data
with open('scripts/data/analysis_20260520_142201.json', 'r') as f:
    data = json.load(f)

reasoning = data['reasoning_comparison']

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Order Quality: Reasoning vs Non-Reasoning Models', fontsize=16, fontweight='bold')

# Colors
reasoning_color = '#2E86AB'  # Blue
non_reasoning_color = '#A23B72'  # Purple

# Plot 1: Invalid Order Rates
categories = ['Reasoning\nModels', 'Non-Reasoning\nModels']
invalid_rates = [
    reasoning['reasoning']['avg_invalid_rate'],
    reasoning['non_reasoning']['avg_invalid_rate']
]

bars1 = ax1.bar(categories, invalid_rates, color=[reasoning_color, non_reasoning_color],
                alpha=0.8, edgecolor='black', linewidth=1.5)

ax1.set_ylabel('Invalid Order Rate (%)', fontsize=12, fontweight='bold')
ax1.set_title('Invalid Order Rates', fontsize=14, fontweight='bold', pad=15)
ax1.set_ylim(0, max(invalid_rates) * 1.2)
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on bars
for bar, value in zip(bars1, invalid_rates):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{value:.1f}%',
             ha='center', va='bottom', fontsize=13, fontweight='bold')

# Add improvement annotation
improvement = invalid_rates[1] - invalid_rates[0]
ax1.annotate(f'{improvement:.1f}% worse\n(1.8x higher)',
             xy=(1, invalid_rates[1]), xytext=(0.5, invalid_rates[1] + 1),
             ha='center', fontsize=10, color='red', fontweight='bold',
             arrowprops=dict(arrowstyle='->', color='red', lw=2))

# Plot 2: Order Complexity (supports/convoys)
complexity = [
    reasoning['reasoning']['avg_complexity'],
    reasoning['non_reasoning']['avg_complexity']
]

bars2 = ax2.bar(categories, complexity, color=[reasoning_color, non_reasoning_color],
                alpha=0.8, edgecolor='black', linewidth=1.5)

ax2.set_ylabel('Complex Orders per Game', fontsize=12, fontweight='bold')
ax2.set_title('Tactical Complexity (Supports + Convoys)', fontsize=14, fontweight='bold', pad=15)
ax2.set_ylim(0, max(complexity) * 1.2)
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on bars
for bar, value in zip(bars2, complexity):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{value:.1f}',
             ha='center', va='bottom', fontsize=13, fontweight='bold')

# Add multiplier annotation
multiplier = complexity[0] / complexity[1]
ax2.annotate(f'{multiplier:.1f}x more\ncomplex tactics',
             xy=(0, complexity[0]), xytext=(0.5, complexity[0] - 3),
             ha='center', fontsize=10, color='green', fontweight='bold',
             arrowprops=dict(arrowstyle='->', color='green', lw=2))

# Add model examples as footnote
fig.text(0.5, 0.02,
         'Reasoning: Claude Opus 4.7, GPT-5.5, DeepSeek-v4-pro  |  '
         'Non-Reasoning: Claude Sonnet, Haiku, GPT-4.1-mini, Gemini, Grok, others',
         ha='center', fontsize=9, style='italic', color='gray')

plt.tight_layout(rect=[0, 0.04, 1, 0.96])
plt.savefig('games/order_quality_analysis.png', dpi=150, bbox_inches='tight')
print("✅ Saved: games/order_quality_analysis.png")
plt.close()
