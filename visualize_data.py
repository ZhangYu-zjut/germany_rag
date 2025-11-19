#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的数据可视化脚本
需要安装: pip install matplotlib pandas
"""

import csv
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime

# 设置中文字体（根据操作系统选择）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


def plot_party_timeline(csv_file='map.csv', output_file='party_timeline.png'):
    """绘制主要党派的时间线图"""
    print("正在生成党派时间线图...")
    
    # 读取数据
    year_party_count = defaultdict(lambda: defaultdict(int))
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = row['年份']
            party = row['所属党派']
            if party != 'None':
                year_party_count[year][party] += 1
    
    # 选择主要党派
    major_parties = ['CDU/CSU', 'SPD', 'FDP', 'GRÜNE', 'Grüne/Bündnis 90', 
                     'DIE LINKE', 'PDS', 'AfD', 'BÜNDNIS 90/DIE GRÜNEN']
    
    # 准备数据
    years = sorted(year_party_count.keys())
    party_data = {party: [] for party in major_parties}
    
    for year in years:
        for party in major_parties:
            party_data[party].append(year_party_count[year][party])
    
    # 绘图
    plt.figure(figsize=(15, 8))
    
    for party in major_parties:
        if sum(party_data[party]) > 0:  # 只绘制有数据的党派
            plt.plot(years, party_data[party], marker='o', label=party, linewidth=2)
    
    plt.xlabel('年份', fontsize=12)
    plt.ylabel('发言记录数', fontsize=12)
    plt.title('德国主要党派议会发言记录时间线 (1949-2021)', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    
    # 只显示部分年份标签以避免拥挤
    ax = plt.gca()
    tick_positions = range(0, len(years), 5)  # 每5年显示一次
    ax.set_xticks([years[i] for i in tick_positions if i < len(years)])
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")
    plt.close()


def plot_party_distribution(csv_file='group.csv', output_file='party_distribution.png'):
    """绘制党派分布饼图"""
    print("正在生成党派分布图...")
    
    # 读取数据
    parties = []
    counts = []
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            party = row['德语名称']
            count = int(row['出现次数'])
            
            # 只显示主要党派，其他归入"其他"
            if count > 5000:
                parties.append(f"{row['中文名称']}\n({row['德语名称']})")
                counts.append(count)
    
    # 创建饼图
    plt.figure(figsize=(12, 8))
    colors = plt.cm.Set3(range(len(parties)))
    
    plt.pie(counts, labels=parties, autopct='%1.1f%%', 
            colors=colors, startangle=90, textprops={'fontsize': 10})
    
    plt.title('德国联邦议院党派发言记录分布 (1949-2021)\n(仅显示记录数>5000的党派)', 
              fontsize=14, fontweight='bold')
    
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")
    plt.close()


def plot_top_speakers(csv_file='map.csv', top_n=20, output_file='top_speakers.png'):
    """绘制发言次数最多的议员柱状图"""
    print("正在生成发言人排名图...")
    
    # 统计每个议员的发言次数
    speaker_count = Counter()
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            speaker_count[row['议员姓名']] += 1
    
    # 获取前N名
    top_speakers = speaker_count.most_common(top_n)
    speakers = [s[0] for s in top_speakers]
    counts = [s[1] for s in top_speakers]
    
    # 绘制横向柱状图
    plt.figure(figsize=(12, 10))
    y_pos = range(len(speakers))
    
    bars = plt.barh(y_pos, counts, color='steelblue')
    
    # 为每个柱子添加数值标签
    for i, (bar, count) in enumerate(zip(bars, counts)):
        plt.text(count, i, f' {count}', va='center', fontsize=9)
    
    plt.yticks(y_pos, speakers, fontsize=9)
    plt.xlabel('发言记录数', fontsize=12)
    plt.title(f'德国联邦议院发言记录数Top {top_n}议员 (1949-2021)', 
              fontsize=14, fontweight='bold')
    plt.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")
    plt.close()


def plot_party_changes(csv_file='map.csv', output_file='party_changes.png'):
    """统计并绘制党派变动情况"""
    print("正在生成党派变动统计图...")
    
    # 统计每个议员的党派数量
    speaker_parties = defaultdict(set)
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            speaker = row['议员姓名']
            party = row['所属党派']
            if party and party != 'None':
                speaker_parties[speaker].add(party)
    
    # 统计党派数量分布
    party_count_distribution = Counter()
    for parties in speaker_parties.values():
        party_count_distribution[len(parties)] += 1
    
    # 准备数据
    party_nums = sorted(party_count_distribution.keys())
    speaker_counts = [party_count_distribution[n] for n in party_nums]
    
    # 绘图
    plt.figure(figsize=(10, 6))
    bars = plt.bar(party_nums, speaker_counts, color='coral', edgecolor='black')
    
    # 添加数值标签
    for bar, count in zip(bars, speaker_counts):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}',
                ha='center', va='bottom', fontsize=10)
    
    plt.xlabel('曾属党派数量', fontsize=12)
    plt.ylabel('议员人数', fontsize=12)
    plt.title('德国联邦议院议员党派变动统计 (1949-2021)', fontsize=14, fontweight='bold')
    plt.xticks(party_nums)
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")
    plt.close()


def plot_yearly_activity(csv_file='map.csv', output_file='yearly_activity.png'):
    """绘制每年的活跃度（发言记录数）"""
    print("正在生成年度活跃度图...")
    
    # 统计每年的记录数
    year_count = Counter()
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year_count[row['年份']] += 1
    
    # 准备数据
    years = sorted(year_count.keys())
    counts = [year_count[year] for year in years]
    
    # 绘图
    plt.figure(figsize=(15, 6))
    plt.plot(years, counts, marker='o', color='green', linewidth=2, markersize=4)
    plt.fill_between(range(len(years)), counts, alpha=0.3, color='green')
    
    plt.xlabel('年份', fontsize=12)
    plt.ylabel('发言记录数', fontsize=12)
    plt.title('德国联邦议院年度发言记录数统计 (1949-2021)', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    
    # 只显示部分年份标签
    ax = plt.gca()
    tick_positions = range(0, len(years), 5)
    ax.set_xticks([years[i] for i in tick_positions if i < len(years)])
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")
    plt.close()


def main():
    """生成所有可视化图表"""
    print("="*80)
    print("德国联邦议院数据可视化")
    print("="*80)
    print("\n开始生成图表...\n")
    
    try:
        # 1. 党派时间线
        plot_party_timeline()
        
        # 2. 党派分布饼图
        plot_party_distribution()
        
        # 3. Top发言人
        plot_top_speakers()
        
        # 4. 党派变动统计
        plot_party_changes()
        
        # 5. 年度活跃度
        plot_yearly_activity()
        
        print("\n" + "="*80)
        print("所有图表生成完成！")
        print("="*80)
        print("\n生成的图表文件:")
        print("  1. party_timeline.png - 党派时间线图")
        print("  2. party_distribution.png - 党派分布饼图")
        print("  3. top_speakers.png - 发言人排名图")
        print("  4. party_changes.png - 党派变动统计图")
        print("  5. yearly_activity.png - 年度活跃度图")
        
    except ImportError as e:
        print(f"\n错误: {e}")
        print("\n请先安装必要的库:")
        print("  pip install matplotlib pandas")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
