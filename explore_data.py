#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据探索脚本 - 用于查看和分析生成的CSV文件
"""

import csv
import pandas as pd
from collections import defaultdict


def explore_group_csv(file_path='group.csv'):
    """探索党派映射表"""
    print("="*80)
    print("党派映射表分析 (group.csv)")
    print("="*80)
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"\n总计党派数量: {len(rows)}")
    
    # 统计需要补充翻译的党派
    needs_translation = [row for row in rows if row['备注'] == '需要补充翻译']
    print(f"需要补充翻译的党派: {len(needs_translation)}")
    
    # 显示主要党派（出现次数>1000）
    print("\n主要党派（出现次数>1000）:")
    major_parties = [row for row in rows if int(row['出现次数']) > 1000]
    for party in major_parties:
        print(f"  {party['德语名称']:40s} -> {party['中文名称']:20s} ({party['出现次数']:>8s}次)")
    
    # 显示稀有党派（出现次数<10）
    print("\n稀有党派（出现次数<10）:")
    rare_parties = [row for row in rows if int(row['出现次数']) < 10]
    for party in rare_parties:
        print(f"  {party['德语名称']:40s} -> {party['中文名称']:20s} ({party['出现次数']:>2s}次)")


def explore_speaker_changes(file_path='map.csv', top_n=20):
    """探索议员党派变动情况"""
    print("\n" + "="*80)
    print("议员党派变动分析 (map.csv)")
    print("="*80)
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"\n总记录数: {len(rows)}")
    
    # 统计每个议员的党派数量
    speaker_parties = defaultdict(set)
    speaker_years = defaultdict(set)
    
    for row in rows:
        speaker = row['议员姓名']
        party = row['所属党派']
        year = row['年份']
        
        if party and party != 'None':
            speaker_parties[speaker].add(party)
            speaker_years[speaker].add(year)
    
    # 找出有党派变动的议员
    changed_speakers = [(speaker, parties, speaker_years[speaker]) 
                       for speaker, parties in speaker_parties.items() 
                       if len(parties) > 1]
    
    # 按年份跨度排序
    changed_speakers.sort(key=lambda x: len(x[2]), reverse=True)
    
    print(f"\n有党派变动的议员总数: {len(changed_speakers)}")
    print(f"\n前{top_n}位活跃且有党派变动的议员:")
    
    for i, (speaker, parties, years) in enumerate(changed_speakers[:top_n], 1):
        year_range = f"{min(years)}-{max(years)}"
        parties_str = " -> ".join(sorted(parties))
        print(f"{i:2d}. {speaker:40s} | {year_range:15s} | {parties_str}")
    
    # 统计党派变动模式
    print("\n\n常见党派变动模式:")
    change_patterns = defaultdict(int)
    
    for speaker, parties, years in changed_speakers:
        pattern = " -> ".join(sorted(parties))
        change_patterns[pattern] += 1
    
    # 显示前10个最常见的变动模式
    for i, (pattern, count) in enumerate(sorted(change_patterns.items(), 
                                                 key=lambda x: x[1], 
                                                 reverse=True)[:10], 1):
        print(f"{i:2d}. {pattern:60s} : {count:3d} 人")


def analyze_party_timeline(file_path='map.csv', party_name='SPD'):
    """分析某个党派的时间线"""
    print("\n" + "="*80)
    print(f"党派时间线分析: {party_name}")
    print("="*80)
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader if row['所属党派'] == party_name]
    
    # 统计每年的议员数
    year_speakers = defaultdict(set)
    
    for row in rows:
        year = row['年份']
        speaker = row['议员姓名']
        year_speakers[year].add(speaker)
    
    print(f"\n{party_name}在各年份的记录数:")
    for year in sorted(year_speakers.keys()):
        print(f"  {year}年: {len(year_speakers[year]):4d} 位不同的发言人")


def find_speaker_info(speaker_name, file_path='map.csv'):
    """查找特定议员的信息"""
    print("\n" + "="*80)
    print(f"议员信息查询: {speaker_name}")
    print("="*80)
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader if speaker_name.lower() in row['议员姓名'].lower()]
    
    if not rows:
        print(f"\n未找到包含'{speaker_name}'的议员")
        return
    
    # 按议员名称分组
    speaker_data = defaultdict(list)
    for row in rows:
        speaker_data[row['议员姓名']].append(row)
    
    for speaker, records in speaker_data.items():
        print(f"\n议员: {speaker}")
        print(f"记录数: {len(records)}")
        
        # 按年份排序
        records.sort(key=lambda x: x['年份'])
        
        print("党派履历:")
        current_party = None
        start_year = None
        
        for record in records:
            year = record['年份']
            party = record['所属党派']
            
            if party != current_party:
                if current_party:
                    print(f"  {start_year}-{prev_year}: {current_party}")
                current_party = party
                start_year = year
            
            prev_year = year
        
        # 打印最后一个党派
        if current_party:
            print(f"  {start_year}-{prev_year}: {current_party}")


def main():
    """主函数 - 提供交互式菜单"""
    
    while True:
        print("\n" + "="*80)
        print("德国议会数据探索工具")
        print("="*80)
        print("\n请选择功能:")
        print("1. 查看党派映射表分析")
        print("2. 查看议员党派变动分析")
        print("3. 分析特定党派的时间线")
        print("4. 查询特定议员信息")
        print("5. 查看所有分析")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-5): ").strip()
        
        if choice == '0':
            print("\n感谢使用！再见！")
            break
        elif choice == '1':
            explore_group_csv()
        elif choice == '2':
            explore_speaker_changes()
        elif choice == '3':
            party = input("\n请输入党派名称 (如: SPD, CDU/CSU, FDP): ").strip()
            if party:
                analyze_party_timeline(party_name=party)
            else:
                print("党派名称不能为空")
        elif choice == '4':
            speaker = input("\n请输入议员姓名（支持模糊查询）: ").strip()
            if speaker:
                find_speaker_info(speaker)
            else:
                print("议员姓名不能为空")
        elif choice == '5':
            explore_group_csv()
            explore_speaker_changes()
            print("\n\n示例：分析SPD党派时间线")
            analyze_party_timeline(party_name='SPD')
            print("\n\n示例：查询包含'Schmidt'的议员")
            find_speaker_info('Schmidt')
        else:
            print("\n无效的选项，请重新选择")
        
        input("\n按回车键继续...")


if __name__ == '__main__':
    # 直接运行所有分析
    print("正在运行完整分析...")
    explore_group_csv()
    explore_speaker_changes()
    
    print("\n\n" + "="*80)
    print("快速示例分析")
    print("="*80)
    
    # 分析几个主要党派
    for party in ['SPD', 'CDU/CSU', 'FDP', 'GRÜNE']:
        try:
            analyze_party_timeline(party_name=party)
        except:
            pass
    
    # 查询几个知名政治家（示例）
    for name in ['Adenauer', 'Schmidt', 'Merkel']:
        try:
            find_speaker_info(name)
        except:
            pass
    
    print("\n\n如需交互式查询，请取消main()函数的注释并重新运行")
    # main()  # 如需交互模式，取消此行注释
