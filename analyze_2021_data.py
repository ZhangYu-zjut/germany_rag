#!/usr/bin/env python3
"""
分析2021年数据文件结构和差异
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter

load_dotenv()
sys.path.append(str(Path(__file__).parent))

from src.utils.logger import logger

def analyze_json_structure(file_path: str, sample_size: int = 10):
    """分析JSON文件结构"""
    
    logger.info(f"📁 分析文件: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        transcript = data.get('transcript', [])
        total_records = len(transcript)
        
        logger.info(f"   总记录数: {total_records:,}")
        
        # 分析前几条记录的结构
        sample_records = transcript[:sample_size]
        
        text_ids = []
        date_info = []
        speakers = []
        
        for i, record in enumerate(sample_records):
            if isinstance(record, dict):
                metadata = record.get('metadata', {})
                text_id = metadata.get('id', 'N/A')
                text_ids.append(text_id)
                
                year = metadata.get('year', '?')
                month = metadata.get('month', '?')
                day = metadata.get('day', '?')
                
                # 安全处理数字格式
                try:
                    if isinstance(month, (int, str)) and str(month).isdigit():
                        month = f"{int(month):02d}"
                    else:
                        month = str(month)
                        
                    if isinstance(day, (int, str)) and str(day).isdigit():
                        day = f"{int(day):02d}"  
                    else:
                        day = str(day)
                        
                    date_str = f"{year}-{month}-{day}"
                except:
                    date_str = f"{year}-{month}-{day}"
                date_info.append(date_str)
                
                speakers.append(metadata.get('speaker', 'N/A'))
                
                if i < 3:  # 详细显示前3条
                    logger.info(f"   记录 {i+1}:")
                    logger.info(f"     text_id: {text_id}")
                    logger.info(f"     日期: {date_str}")
                    logger.info(f"     发言人: {metadata.get('speaker', 'N/A')}")
                    logger.info(f"     session: {metadata.get('session', 'N/A')}")
                    speech_preview = record.get('speech', '')[:50] + '...' if len(record.get('speech', '')) > 50 else record.get('speech', '')
                    logger.info(f"     speech预览: {speech_preview}")
        
        # text_id模式分析
        logger.info(f"\n📊 text_id 模式分析:")
        if text_ids:
            id_patterns = set()
            for text_id in text_ids[:20]:  # 分析前20个
                if isinstance(text_id, str):
                    # 提取模式：保留数字和分隔符的模式
                    import re
                    pattern = re.sub(r'\d+', 'N', str(text_id))
                    id_patterns.add(pattern)
            
            for pattern in sorted(id_patterns):
                count = sum(1 for tid in text_ids if re.sub(r'\d+', 'N', str(tid)) == pattern)
                logger.info(f"   模式 '{pattern}': {count} 个")
        
        # 日期分布
        date_counter = Counter(date_info)
        logger.info(f"\n📅 日期分布 (前5个):")
        for date, count in date_counter.most_common(5):
            logger.info(f"   {date}: {count} 条记录")
            
        # 发言人统计
        speaker_counter = Counter(speakers)
        logger.info(f"\n👥 主要发言人 (前5个):")
        for speaker, count in speaker_counter.most_common(5):
            logger.info(f"   {speaker}: {count} 条记录")
            
        return {
            'file_path': file_path,
            'total_records': total_records,
            'text_ids': text_ids[:20],  # 保存前20个text_id用于对比
            'date_distribution': dict(date_counter.most_common(10)),
            'speaker_distribution': dict(speaker_counter.most_common(10))
        }
        
    except Exception as e:
        logger.error(f"❌ 分析文件失败: {str(e)}")
        return None

def compare_file_structures(file1_info: dict, file2_info: dict):
    """对比两个文件的结构差异"""
    
    logger.info(f"\n🔍 文件结构对比分析")
    logger.info("=" * 60)
    
    # 基本信息对比
    logger.info(f"\n📊 基本信息对比:")
    logger.info(f"   文件1 ({Path(file1_info['file_path']).name}): {file1_info['total_records']:,} 条记录")
    logger.info(f"   文件2 ({Path(file2_info['file_path']).name}): {file2_info['total_records']:,} 条记录")
    
    total_records = file1_info['total_records'] + file2_info['total_records']
    logger.info(f"   合计: {total_records:,} 条记录")
    
    # text_id模式对比
    logger.info(f"\n🆔 text_id 样本对比:")
    logger.info(f"   文件1样本: {file1_info['text_ids'][:5]}")
    logger.info(f"   文件2样本: {file2_info['text_ids'][:5]}")
    
    # 检查text_id是否有重叠
    set1 = set(file1_info['text_ids'])
    set2 = set(file2_info['text_ids']) 
    overlap = set1.intersection(set2)
    
    if overlap:
        logger.warning(f"⚠️  发现text_id重叠: {len(overlap)} 个")
        logger.info(f"   重叠示例: {list(overlap)[:3]}")
    else:
        logger.info(f"✅ text_id无重叠，可以安全合并")
    
    # 日期分布对比
    logger.info(f"\n📅 日期分布对比:")
    logger.info(f"   文件1主要日期: {list(file1_info['date_distribution'].keys())[:3]}")
    logger.info(f"   文件2主要日期: {list(file2_info['date_distribution'].keys())[:3]}")

def main():
    """主函数"""
    logger.info("🔍 开始分析2021年数据文件")
    logger.info("=" * 60)
    
    # 分析两个文件
    file1 = "data/pp_json_49-21/pp_2021.json"
    file2 = "data/pp_json_49-21/pp_2021 (2).json"
    
    file1_info = analyze_json_structure(file1)
    logger.info("\n" + "-" * 60)
    file2_info = analyze_json_structure(file2)
    
    if file1_info and file2_info:
        compare_file_structures(file1_info, file2_info)
        
        # 合并建议
        logger.info(f"\n💡 合并建议:")
        logger.info(f"   1. 两文件结构相似，可以直接合并transcript数组")
        logger.info(f"   2. 合并后总记录数: {file1_info['total_records'] + file2_info['total_records']:,}")
        logger.info(f"   3. 建议生成新文件: pp_2021_merged.json")
    else:
        logger.error("❌ 文件分析失败")

if __name__ == "__main__":
    main()
