#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析德国议会JSON数据的metadata
提取group和speaker字段，并生成映射表
"""

import json
import os
from collections import defaultdict, Counter
import csv
import glob


def load_json_files(directory):
    """加载指定目录下的所有JSON文件"""
    json_files = glob.glob(os.path.join(directory, "pp_*.json"))
    json_files.sort()
    return json_files


def extract_metadata(json_file):
    """从JSON文件中提取所有metadata"""
    metadata_list = []
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 提取年份信息
        session_year = data.get('session', 'unknown')
        
        # 遍历transcript中的所有记录
        for item in data.get('transcript', []):
            if 'metadata' in item:
                metadata = item['metadata'].copy()
                metadata['file'] = os.path.basename(json_file)
                
                # 清理speaker字段中的特殊字符（德语引号等）
                speaker = metadata.get('speaker', '')
                # 移除开头的德语双引号 „ 和 "
                speaker = speaker.lstrip('„"“„')
                speaker = speaker.rstrip('"””')
                speaker = speaker.strip()
                metadata['speaker'] = speaker
                
                metadata_list.append(metadata)
                
    except Exception as e:
        print(f"处理文件 {json_file} 时出错: {e}")
    
    return metadata_list


def analyze_distribution(all_metadata):
    """分析group和speaker的分布情况"""
    group_counter = Counter()
    speaker_counter = Counter()
    
    # 按年份统计group分布
    group_by_year = defaultdict(Counter)
    speaker_by_year = defaultdict(Counter)
    
    # 议员-党派-年份映射
    speaker_group_year = defaultdict(lambda: defaultdict(set))
    
    for meta in all_metadata:
        year = meta.get('year', 'unknown')
        group = meta.get('group', 'None')
        speaker = meta.get('speaker', 'unknown')
        
        # 统计总体分布
        group_counter[group] += 1
        speaker_counter[speaker] += 1
        
        # 按年份统计
        group_by_year[year][group] += 1
        speaker_by_year[year][speaker] += 1
        
        # 记录议员-党派-年份关系
        if speaker != 'unknown' and group != 'None':
            speaker_group_year[speaker][year].add(group)
    
    return {
        'group_counter': group_counter,
        'speaker_counter': speaker_counter,
        'group_by_year': group_by_year,
        'speaker_by_year': speaker_by_year,
        'speaker_group_year': speaker_group_year
    }


def print_distribution_stats(stats):
    """打印分布统计信息"""
    print("\n" + "="*80)
    print("党派(GROUP)分布统计")
    print("="*80)
    
    print(f"\n总计发现 {len(stats['group_counter'])} 个不同的党派:")
    for group, count in stats['group_counter'].most_common():
        percentage = count / sum(stats['group_counter'].values()) * 100
        print(f"  {group}: {count:,} 次 ({percentage:.2f}%)")
    
    print("\n" + "="*80)
    print("发言人(SPEAKER)分布统计")
    print("="*80)
    
    print(f"\n总计发现 {len(stats['speaker_counter'])} 个不同的发言人")
    print(f"\n发言次数前20的议员:")
    for speaker, count in stats['speaker_counter'].most_common(20):
        print(f"  {speaker}: {count:,} 次")
    
    # 按年份统计党派分布
    print("\n" + "="*80)
    print("各年份党派分布概况")
    print("="*80)
    
    years = sorted(stats['group_by_year'].keys())
    for year in years[:5]:  # 只显示前5年作为示例
        print(f"\n{year}年:")
        for group, count in stats['group_by_year'][year].most_common():
            print(f"  {group}: {count:,} 次")


def create_group_mapping():
    """创建党派名称映射表（德语->中文）"""
    # 德国主要党派的中文翻译
    group_mapping = {
        "CDU/CSU": "基民盟/基社盟",
        "SPD": "社民党",
        "FDP": "自民党",
        "BÜNDNIS 90/DIE GRÜNEN": "绿党",
        "BÜNDNIS 90/DIE GRÜNEN": "绿党",
        "BÜNDNIS 90/DIE GRÜNE N": "绿党",
        "DIE GRÜNEN": "绿党",
        "GRÜNE": "绿党",
        "Grüne/Bündnis 90": "绿党",
        "Bündnis 90/Die Grünen": "绿党",
        "AfD": "德国选择党",
        "DIE LINKE": "左翼党",
        "Die Linke": "左翼党",
        "PDS": "民主社会主义党",
        "PDS/Linke Liste": "民主社会主义党/左翼名单",
        "KPD": "德国共产党",
        "BP": "巴伐利亚党",
        "DP": "德国党",
        "DP [FVP]": "德国党[自由人民党]",
        "WAV": "经济重建联盟",
        "DPB": "德国人民党",
        "Z": "中央党",
        "Zentrum": "中央党",
        "GB/BHE": "全德国集团/无家可归者和剥夺权利者联盟",
        "BHE": "无家可归者和剥夺权利者联盟",
        "BHE-DG": "无家可归者联盟-全德国集团",
        "DA": "德国联盟",
        "SSW": "南石勒苏益格选民协会",
        "FU": "全德国联盟",
        "DRP": "德国帝国党",
        "SRP": "社会主义帝国党",
        "FPD": "自由人民党(可能为FDP错误标注)",
        "FVP": "自由人民党",
        "SDP": "社会民主党(可能为SPD错误标注)",
        "NR": "国民代表(可能为某地区联盟)",
        "NDP": "德国国家民主党",
        "EDP": "欧洲民主党",
        "MP": "议员(可能为无党派)",
        "Fraktionslos": "无党派",
        "fraktionslos": "无党派",
        "None": "无党派/未标注",
        "Parteilos": "无党派",
        "Unabhängig": "独立/无党派",
        # 客座议员标注
        "FDP-Gast": "自民党-客座议员",
        "SPD-Gast": "社民党-客座议员",
        "CDU/CSU-Gast": "基民盟/基社盟-客座议员",
        "DP-Gast": "德国党-客座议员",
        "FU-Gast": "全德国联盟-客座议员",
        "FPD-Gast": "自由人民党-客座议员",
        "DRP-Gast": "德国帝国党-客座议员",
        # 待客或临时成员
        "FDP-Hosp.": "自民党-候补议员",
        "DRP-Hosp.": "德国帝国党-候补议员",
        "CDU/CSU-Hosp.": "基民盟/基社盟-候补议员",
        # 联合党派
        "DP/DPB": "德国党/德国人民党",
        # 城市或地区名称（可能为地区代表）
        "Wuppertal": "伍珀塔尔地区代表",
        "Bremen": "不莱梅地区代表"
    }
    
    return group_mapping


def save_group_mapping(group_counter, output_file='group.csv'):
    """保存党派映射表到CSV文件"""
    group_mapping = create_group_mapping()
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['德语名称', '中文名称', '出现次数', '备注'])
        
        # 按出现次数排序
        for group, count in sorted(group_counter.items(), key=lambda x: x[1], reverse=True):
            chinese_name = group_mapping.get(group, '待翻译')
            
            # 添加备注信息
            if group == 'None':
                note = '无党派或未标注'
            elif chinese_name == '待翻译':
                note = '需要补充翻译'
            else:
                note = ''
            
            writer.writerow([group, chinese_name, count, note])
    
    print(f"\n党派映射表已保存到: {output_file}")


def save_speaker_group_mapping(speaker_group_year, output_file='map.csv'):
    """保存议员-党派动态映射表到CSV文件"""
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['议员姓名', '年份', '所属党派', '备注'])
        
        # 按议员名称排序
        for speaker in sorted(speaker_group_year.keys()):
            year_groups = speaker_group_year[speaker]
            
            # 按年份排序
            for year in sorted(year_groups.keys()):
                groups = year_groups[year]
                
                # 如果一个议员在同一年属于多个党派，添加备注
                if len(groups) > 1:
                    note = f'该年属于多个党派: {", ".join(groups)}'
                    for group in sorted(groups):
                        writer.writerow([speaker, year, group, note])
                else:
                    group = list(groups)[0]
                    writer.writerow([speaker, year, group, ''])
    
    print(f"议员-党派映射表已保存到: {output_file}")


def generate_summary_report(stats, output_file='summary_report.txt'):
    """生成详细的统计分析报告"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("德国联邦议院议会记录 Metadata 分析报告\n")
        f.write("="*80 + "\n\n")
        
        # 1. 党派统计
        f.write("一、党派(GROUP)分布统计\n")
        f.write("-"*80 + "\n")
        f.write(f"总计发现 {len(stats['group_counter'])} 个不同的党派\n\n")
        
        for group, count in stats['group_counter'].most_common():
            percentage = count / sum(stats['group_counter'].values()) * 100
            f.write(f"{group:40s}: {count:8,} 次 ({percentage:6.2f}%)\n")
        
        # 2. 发言人统计
        f.write("\n\n二、发言人(SPEAKER)分布统计\n")
        f.write("-"*80 + "\n")
        f.write(f"总计发现 {len(stats['speaker_counter'])} 个不同的发言人\n\n")
        f.write("发言次数前50的议员:\n")
        
        for i, (speaker, count) in enumerate(stats['speaker_counter'].most_common(50), 1):
            f.write(f"{i:3d}. {speaker:40s}: {count:6,} 次\n")
        
        # 3. 年份统计
        f.write("\n\n三、各年份党派分布详情\n")
        f.write("-"*80 + "\n")
        
        years = sorted(stats['group_by_year'].keys())
        for year in years:
            f.write(f"\n{year}年:\n")
            year_total = sum(stats['group_by_year'][year].values())
            for group, count in stats['group_by_year'][year].most_common():
                percentage = count / year_total * 100
                f.write(f"  {group:35s}: {count:6,} 次 ({percentage:6.2f}%)\n")
        
        # 4. 党派变动分析
        f.write("\n\n四、议员党派变动情况\n")
        f.write("-"*80 + "\n")
        
        # 查找有党派变动的议员
        changed_speakers = []
        for speaker, year_groups in stats['speaker_group_year'].items():
            all_groups = set()
            for groups in year_groups.values():
                all_groups.update(groups)
            
            # 过滤掉None
            all_groups = {g for g in all_groups if g != 'None'}
            
            if len(all_groups) > 1:
                changed_speakers.append((speaker, year_groups, all_groups))
        
        f.write(f"发现 {len(changed_speakers)} 位议员有党派变动记录:\n\n")
        
        for speaker, year_groups, all_groups in sorted(changed_speakers)[:50]:
            f.write(f"{speaker}:\n")
            for year in sorted(year_groups.keys()):
                groups = ', '.join(sorted(year_groups[year]))
                f.write(f"  {year}年: {groups}\n")
            f.write("\n")
    
    print(f"详细分析报告已保存到: {output_file}")


def main():
    """主函数"""
    # 数据目录
    data_dir = "data/pp_json_49-21"
    
    print("开始解析JSON文件...")
    print(f"数据目录: {data_dir}")
    
    # 获取所有JSON文件
    json_files = load_json_files(data_dir)
    print(f"找到 {len(json_files)} 个JSON文件")
    
    # 提取所有metadata
    all_metadata = []
    for i, json_file in enumerate(json_files, 1):
        print(f"处理文件 {i}/{len(json_files)}: {os.path.basename(json_file)}")
        metadata_list = extract_metadata(json_file)
        all_metadata.extend(metadata_list)
    
    print(f"\n总计提取了 {len(all_metadata):,} 条metadata记录")
    
    # 分析分布情况
    print("\n开始分析数据分布...")
    stats = analyze_distribution(all_metadata)
    
    # 打印统计信息
    print_distribution_stats(stats)
    
    # 保存党派映射表
    print("\n生成党派映射表...")
    save_group_mapping(stats['group_counter'], 'group.csv')
    
    # 保存议员-党派映射表
    print("\n生成议员-党派映射表...")
    save_speaker_group_mapping(stats['speaker_group_year'], 'map.csv')
    
    # 生成详细报告
    print("\n生成详细分析报告...")
    generate_summary_report(stats, 'summary_report.txt')
    
    print("\n" + "="*80)
    print("所有任务完成!")
    print("="*80)
    print("\n生成的文件:")
    print("  1. group.csv - 党派名称映射表（德语->中文）")
    print("  2. map.csv - 议员-党派动态映射表")
    print("  3. summary_report.txt - 详细统计分析报告")


if __name__ == '__main__':
    main()
