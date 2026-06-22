#!/usr/bin/env python
"""Generate all chart PNGs for The Complexity Paradox website.
Called by Flask admin after adding games, or run manually.
"""

import matplotlib
matplotlib.use('Agg')  # Headless backend — must be before pyplot import
import sys
import os
import shutil
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats

# Find project root regardless of where script is called from
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add scripts to path for db_connect
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))
from db_connect import get_connection


def load_data():
    """Load games and engines from database."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM games", conn)
    engines_df = pd.read_sql_query("SELECT * FROM engines", conn)
    conn.close()
    return df, engines_df


def clear_output_dir(output_dir):
    """Remove old PNGs and recreate folder."""
    out = Path(output_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    return out


def generate_q1(df, output_dir):
    """Q1 - Development Time Over Decades (scatter + trend)."""
    q1_df = df.dropna(subset=['development_time', 'release_year'])
    plt.figure(figsize=(12, 7))

    colors = {'AAA': '#e74c3c', 'AA': '#3498db', 'Indie': '#2ecc71'}

    for game_type, group in q1_df.groupby('game_type'):
        jitter = np.random.uniform(-1.5, 1.5, size=len(group))
        plt.scatter(group['release_year'], group['development_time'] + jitter,
                    c=colors[game_type], label=game_type, alpha=0.7, s=80)

    # Trend line
    z = np.polyfit(q1_df['release_year'], q1_df['development_time'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(q1_df['release_year'].min(), q1_df['release_year'].max(), 100)
    plt.plot(x_line, p(x_line), 'k--', linewidth=2, label='Trend')

    # Annotate max dev time game
    max_game = q1_df.loc[q1_df['development_time'].idxmax()]
    plt.annotate(f"{max_game['name']}\n({int(max_game['development_time'])} months)",
                 xy=(max_game['release_year'], max_game['development_time']),
                 xytext=(max_game['release_year'] - 12, max_game['development_time'] - 15),
                 fontsize=9,
                 arrowprops=dict(arrowstyle='->', color='black'))

    plt.xlabel('Release Year', fontsize=12)
    plt.ylabel('Development Time (Months)', fontsize=12)
    plt.title('Game Development Time Over the Decades', fontsize=14)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q1_dev_time_over_years.png', dpi=150)
    plt.close()


def generate_q2(df, output_dir):
    """Q2 - Correlation heatmap."""
    numerical_cols = ['release_year', 'budget', 'file_size', 'peak_team_size',
                      'development_time', 'metacritic_score']
    corr_df = df[numerical_cols].dropna()

    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_df.corr(),
                annot=True,
                fmt='.2f',
                cmap='coolwarm',
                center=0,
                square=True,
                linewidth=0.5)
    plt.title('Correlation Between Game Development Metrics', fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q2_correlation_heatmap.png', dpi=150)
    plt.close()


def generate_q2b(df, output_dir):
    """Q2b - Strongest correlations scatter plots."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Budget vs Team Size
    q2_df = df.dropna(subset=['budget', 'peak_team_size'])
    axes[0].scatter(q2_df['budget'], q2_df['peak_team_size'],
                    alpha=0.7, color='#e74c3c', s=80)
    axes[0].set_yscale('log')
    axes[0].set_xscale('log')
    axes[0].set_xlabel('Budget (USD) - Log Scale', fontsize=11)
    axes[0].set_ylabel('Peak Team Size - Log Scale', fontsize=11)
    axes[0].set_title('Budget vs Team Size (r=0.77)', fontsize=12)

    # File Size vs Release Year
    q2_df2 = df.dropna(subset=['file_size', 'release_year'])
    q2_df2 = q2_df2[q2_df2['file_size'] > 0]
    axes[1].scatter(q2_df2['release_year'], q2_df2['file_size'],
                    alpha=0.7, color='#3498db', s=80)
    axes[1].set_yscale('log')
    axes[1].set_xlabel('Release Year', fontsize=11)
    axes[1].set_ylabel('File Size MB - Log Scale', fontsize=11)
    axes[1].set_title('File Size Growth Over Time (r=0.74)', fontsize=12)

    plt.suptitle('Strongest Correlations in Game Development', fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q2_scatter_correlations.png', dpi=150)
    plt.close()


def generate_q3(df, output_dir):
    """Q3 - How Development Scaled Over Decades."""
    q3_df = df.dropna(subset=['development_time', 'peak_team_size'])

    era_order = ['1980s', '1990s', '2000s', '2010s', '2020s']
    era_dev_time = q3_df.groupby('era')['development_time'].mean().reindex(era_order)
    era_team_size = q3_df.groupby('era')['peak_team_size'].mean().reindex(era_order)

    x = np.arange(len(era_order))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(12, 7))

    bars1 = ax1.bar(x - width / 2, era_dev_time, width,
                    label='Avg Dev Time (Months)', color='#e74c3c', alpha=0.8)
    ax1.set_xlabel('Era', fontsize=12)
    ax1.set_ylabel('Average Development Time (Months)', fontsize=12, color='#e74c3c')
    ax1.tick_params(axis='y', labelcolor='#e74c3c')

    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width / 2, era_team_size, width,
                    label='Avg Team Size', color='#3498db', alpha=0.8)
    ax2.set_ylabel('Average Peak Team Size', fontsize=12, color='#3498db')
    ax2.tick_params(axis='y', labelcolor='#3498db')

    for bar in bars1:
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{bar.get_height():.1f}', ha='center', va='bottom',
                 fontsize=9, color='#e74c3c')

    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{bar.get_height():.0f}', ha='center', va='bottom',
                 fontsize=9, color='#3498db')

    ax1.set_xticks(x)
    ax1.set_xticklabels(era_order, fontsize=11)
    ax1.set_title('How Game Development Scaled Over the Decades', fontsize=14)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/q3_era_dev_time_team_size.png', dpi=150)
    plt.close()


def generate_q4(df, output_dir):
    """Q4 - Franchise vs Original IP Budget."""
    q4_df = df.dropna(subset=['budget']).copy()
    q4_df['ip_type'] = q4_df['franchise_name'].apply(
        lambda x: 'Original IP' if x == 'Standalone' else 'Franchise Entry'
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    sns.boxplot(data=q4_df, x='ip_type', y='budget',
                palette={'Original IP': '#2ecc71', 'Franchise Entry': '#e74c3c'},
                ax=axes[0])
    axes[0].set_title('Budget Distribution by IP Type', fontsize=12)
    axes[0].set_xlabel('IP Type', fontsize=11)
    axes[0].set_ylabel('Budget (USD)', fontsize=11)

    avg_budget = q4_df.groupby('ip_type')['budget'].mean()
    axes[1].bar(avg_budget.index, avg_budget.values,
                color=['#e74c3c', '#2ecc71'], alpha=0.8)
    for i, (idx, val) in enumerate(avg_budget.items()):
        axes[1].text(i, val + 1000000, f'${val / 1e6:.1f}M',
                     ha='center', fontsize=11)

    axes[1].set_title('Average Budget by IP Type', fontsize=12)
    axes[1].set_xlabel('IP Type', fontsize=11)
    axes[1].set_ylabel('Average Budget (USD)', fontsize=11)

    plt.suptitle('Do Franchise Games Cost More to Make?', fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q4_franchise_vs_original_budget.png', dpi=150)
    plt.close()


def generate_q5(df, output_dir):
    """Q5 - Franchise Growth Over Time."""
    franchise_counts = df['franchise_name'].value_counts()
    multi_entry = franchise_counts[franchise_counts >= 2].index.tolist()
    multi_entry = [f for f in multi_entry if f != 'Standalone']

    q5_df = df[df['franchise_name'].isin(multi_entry)]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']

    # Budget growth
    ax = axes[0]
    for i, franchise in enumerate(multi_entry):
        fdf = q5_df[q5_df['franchise_name'] == franchise].dropna(subset=['budget']).sort_values('release_year')
        if len(fdf) >= 2:
            ax.plot(fdf['release_year'], fdf['budget'],
                    marker='o', label=franchise, color=colors[i % len(colors)], linewidth=2)
    ax.set_xlabel('Release Year', fontsize=11)
    ax.set_ylabel('Budget (USD)', fontsize=11)
    ax.set_title('Budget Growth Per Franchise', fontsize=12)
    ax.legend(fontsize=8)

    # File size growth
    ax2 = axes[1]
    for i, franchise in enumerate(multi_entry):
        fdf = q5_df[q5_df['franchise_name'] == franchise].dropna(subset=['file_size']).sort_values('release_year')
        if len(fdf) >= 2:
            ax2.plot(fdf['release_year'], fdf['file_size'],
                     marker='o', label=franchise, color=colors[i % len(colors)], linewidth=2)
    ax2.set_xlabel('Release Year', fontsize=11)
    ax2.set_yscale('log')
    ax2.set_ylabel('File Size (MB) - Log Scale', fontsize=11)
    ax2.set_title('File Size Growth Per Franchise', fontsize=12)
    ax2.legend(fontsize=8)

    plt.suptitle('How Franchises Grew Over Time', fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q5_franchise_growth.png', dpi=150)
    plt.close()


def generate_q6(df, output_dir):
    """Q6 - File Size vs Budget Growth."""
    q6_budget = df.dropna(subset=['budget', 'release_year']).sort_values('release_year')
    q6_file = df.dropna(subset=['file_size', 'release_year']).sort_values('release_year')

    era_order = ['1980s', '1990s', '2000s', '2010s', '2020s']
    avg_budget_era = q6_budget.groupby('era')['budget'].mean().reindex(era_order)
    avg_file_era = q6_file.groupby('era')['file_size'].mean().reindex(era_order)

    budget_normalized = (avg_budget_era / avg_budget_era.iloc[0]) * 100
    file_normalized = (avg_file_era / avg_file_era.iloc[0]) * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Normalized lines
    axes[0].plot(era_order, budget_normalized.values,
                 marker='o', color='#e74c3c', linewidth=2, label='Budget Growth')
    axes[0].plot(era_order, file_normalized.values,
                 marker='o', color='#3498db', linewidth=2, label='File Size Growth')
    axes[0].set_xlabel('Era', fontsize=11)
    axes[0].set_ylabel('Growth Index (Base = 100)', fontsize=11)
    axes[0].set_title('File Size vs Budget Growth\n(Normalized to 1980s = 100)', fontsize=12)
    axes[0].legend(fontsize=10)
    axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
    axes[0].tick_params(axis='x', rotation=45)

    for i, (b, f) in enumerate(zip(budget_normalized.values, file_normalized.values)):
        if not np.isnan(b):
            axes[0].annotate(f'{b:.0f}', (era_order[i], b),
                             textcoords='offset points', xytext=(0, 8),
                             ha='center', fontsize=8, color='#e74c3c')
        if not np.isnan(f):
            axes[0].annotate(f'{f:.0f}', (era_order[i], f),
                             textcoords='offset points', xytext=(0, 8),
                             ha='center', fontsize=8, color='#3498db')

    # Bar chart
    x = np.arange(len(era_order))
    width = 0.35
    ax2 = axes[1]
    ax2_twin = ax2.twinx()

    bars1 = ax2.bar(x - width / 2, avg_budget_era.values, width,
                    color='#e74c3c', alpha=0.8, label='Avg Budget')
    bars2 = ax2_twin.bar(x + width / 2, avg_file_era.values, width,
                         color='#3498db', alpha=0.8, label='Avg File Size')

    ax2.set_xlabel('Era', fontsize=11)
    ax2.set_ylabel('Average Budget (USD)', fontsize=11, color='#e74c3c')
    ax2_twin.set_ylabel('Average File Size (MB)', fontsize=11, color='#3498db')
    ax2.set_xticks(x)
    ax2.set_xticklabels(era_order, rotation=45)
    ax2.set_title('Average Budget vs File Size Per Era', fontsize=12)

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.suptitle('Did File Size Grow Faster Than Budget?', fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q6_filesize_vs_budget_growth.png', dpi=150)
    plt.close()


def generate_q7(df, output_dir):
    """Q7 - Engine Type vs Development Time."""
    # Categorize engines
    def categorize_engine(engine):
        if 'Unreal' in str(engine):
            return 'Unreal'
        elif engine == 'Unity':
            return 'Unity'
        elif engine in ['Source Engine', 'GoldSrc', 'Source 1']:
            return 'Source'
        elif engine == 'Proprietary':
            return 'Proprietary'
        else:
            return 'Other Licensed'

    df['engine_category'] = df['engine'].apply(categorize_engine)
    q7_df = df.dropna(subset=['development_time'])

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    sns.boxplot(data=q7_df, x='engine_category', y='development_time',
                palette='Set2', ax=axes[0])
    axes[0].set_title('Development Time by Engine Type', fontsize=12)
    axes[0].set_xlabel('Engine Category', fontsize=11)
    axes[0].set_ylabel('Development Time (Months)', fontsize=11)
    axes[0].tick_params(axis='x', rotation=15)

    avg_dev = q7_df.groupby('engine_category')['development_time'].mean().sort_values()
    axes[1].bar(avg_dev.index, avg_dev.values, color='#3498db', alpha=0.8)
    for i, (idx, val) in enumerate(avg_dev.items()):
        axes[1].text(i, val + 0.5, f'{val:.1f}', ha='center', fontsize=10)
    axes[1].set_title('Average Development Time by Engine Type', fontsize=12)
    axes[1].set_xlabel('Engine Category', fontsize=11)
    axes[1].set_ylabel('Average Development Time (Months)', fontsize=11)
    axes[1].tick_params(axis='x', rotation=15)

    plt.suptitle('Did Engine Choice Affect Development Time?', fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q7_engine_efficiency.png', dpi=150)
    plt.close()


def generate_q9(df, output_dir):
    """Q9 - File Size vs Metacritic Score."""
    q9_df = df.dropna(subset=['file_size', 'metacritic_score']).copy()

    plt.figure(figsize=(12, 7))
    colors = {'AAA': '#e74c3c', 'AA': '#3498db', 'Indie': '#2ecc71'}

    for game_type, group in q9_df.groupby('game_type'):
        plt.scatter(group['file_size'], group['metacritic_score'],
                    c=colors[game_type], label=game_type, alpha=0.7, s=80)

    # Regression line
    z = np.polyfit(q9_df['file_size'], q9_df['metacritic_score'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(q9_df['file_size'].min(), q9_df['file_size'].max(), 100)
    plt.plot(x_line, p(x_line), 'k--', linewidth=2, label='Trend')

    # Spearman correlation
    corr, pvalue = stats.spearmanr(q9_df['file_size'], q9_df['metacritic_score'])

    plt.xlabel('File Size (MB)', fontsize=12)
    plt.ylabel('Metacritic Score', fontsize=12)
    plt.title(f'Does Bigger Mean Better?\nFile Size vs Metacritic Score '
              f'(Spearman r={corr:.2f}, p={pvalue:.3f})', fontsize=13)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{output_dir}/q9_filesize_vs_metacritic.png', dpi=150)
    plt.close()


def generate_all_charts(output_dir=None):
    """Main entry point. Generate all charts."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / 'outputs' / 'charts'
    else:
        output_dir = Path(output_dir)

    print(f"Loading data...")
    df, _ = load_data()
    print(f"Loaded {len(df)} games")

    print(f"Clearing {output_dir}...")
    clear_output_dir(output_dir)

    charts = [
        ('Q1 - Development Time', generate_q1),
        ('Q2 - Correlation Heatmap', generate_q2),
        ('Q2b - Scatter Correlations', generate_q2b),
        ('Q3 - Era Scaling', generate_q3),
        ('Q4 - Franchise vs Original', generate_q4),
        ('Q5 - Franchise Growth', generate_q5),
        ('Q6 - File Size vs Budget', generate_q6),
        ('Q7 - Engine Efficiency', generate_q7),
        ('Q9 - File Size vs Metacritic', generate_q9),
    ]

    for name, func in charts:
        print(f"Generating {name}...")
        try:
            func(df, output_dir)
            print(f"  ✓ Done")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\nAll charts saved to {output_dir}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate chart PNGs for The Complexity Paradox')
    parser.add_argument('--output-dir', help='Output directory (default: ../outputs/charts)')
    args = parser.parse_args()

    generate_all_charts(args.output_dir)