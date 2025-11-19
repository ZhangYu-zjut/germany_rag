#!/usr/bin/env python3
"""
重新生成Q4/Q5/Q6/Q7的完整引用报告
使用现有的raw_data.json，只重新生成full_report.md
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, '/home/zhangyu/project/rag_germant')

from generate_full_ref_report import FullRefReportGenerator
from src.utils.logger import logger

def regenerate_reports_for_questions(questions=['Q4', 'Q5', 'Q6', 'Q7']):
    """重新生成指定问题的报告"""
    
    generator = FullRefReportGenerator(output_dir="outputs")
    
    for qid in questions:
        logger.info(f"{'='*80}")
        logger.info(f"重新生成 {qid} 的报告")
        logger.info(f"{'='*80}")
        
        # 查找最新的输出目录
        import glob
        dirs = glob.glob(f'outputs/{qid}_20251113_*')
        if not dirs:
            logger.warning(f"❌ {qid}: 没有找到输出目录，跳过")
            continue
        
        latest_dir = Path(sorted(dirs)[-1])
        raw_data_file = latest_dir / f"{qid}_raw_data.json"
        
        if not raw_data_file.exists():
            logger.warning(f"❌ {qid}: raw_data.json不存在，跳过")
            continue
        
        # 读取raw_data
        with open(raw_data_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        logger.info(f"📁 使用目录: {latest_dir}")
        
        # 重新生成报告（只生成markdown，不重新生成JSON）
        try:
            generator._generate_markdown_report(state, latest_dir, qid)
            logger.info(f"✅ {qid}: 报告重新生成成功")
            
            # 验证引用提取
            with open(latest_dir / f"{qid}_full_report.md", 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            match = re.search(r'\*\*共找到 (\d+) 个引用\*\*', content)
            if match:
                count = int(match.group(1))
                matched = content.count('**匹配到')
                logger.info(f"   {qid}: {count}个引用, {matched}个匹配成功")
            
        except Exception as e:
            logger.error(f"❌ {qid}: 报告生成失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n✅ 全部完成！")

if __name__ == "__main__":
    regenerate_reports_for_questions(['Q4', 'Q5', 'Q6', 'Q7'])
