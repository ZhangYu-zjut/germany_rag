#!/usr/bin/env python3
"""
快速测试Q1和Q5报告生成修复
"""
import sys
sys.path.insert(0, '/home/zhangyu/project/rag_germant')

from pathlib import Path
from src.config import settings
from src.graph.workflow import create_graph
from loguru import logger
import time

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)


def test_question(question: str, qid: str):
    """测试单个问题"""
    logger.info(f"\n{'='*100}")
    logger.info(f"测试 {qid}")
    logger.info(f"{'='*100}")
    logger.info(f"问题: {question}")

    # 创建工作流
    graph = create_graph()

    # 初始状态
    initial_state = {
        "question": question,
        "full_ref": True,  # 启用完整引用模式
    }

    try:
        start_time = time.time()

        # 执行工作流
        logger.info("开始执行工作流...")
        final_state = graph.invoke(initial_state)

        elapsed = time.time() - start_time
        logger.info(f"✅ 工作流执行完成，耗时: {elapsed:.1f}秒")

        # 生成完整引用报告
        logger.info("开始生成报告...")
        from generate_full_ref_report import FullRefReportGenerator

        generator = FullRefReportGenerator(output_dir="outputs")
        report_dir = generator.generate_report(final_state, question_id=qid)

        logger.info(f"✅ 报告生成成功: {report_dir}")

        # 检查报告文件
        report_file = report_dir / f"{qid}_full_report.md"
        if report_file.exists():
            file_size = report_file.stat().st_size / 1024  # KB
            logger.info(f"✅ 报告文件大小: {file_size:.1f} KB")
            return True
        else:
            logger.error(f"❌ 报告文件未生成: {report_file}")
            return False

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""

    # Q1和Q5的问题
    questions = {
        "Q1": "Welche Positionen vertraten die verschiedenen Parteien im Deutschen Bundestag zur Flüchtlingspolitik im Jahr 2015?",
        "Q5": "Wie hat sich die Position der Grünen zur Digitalisierung und zur Klimapolitik zwischen 2015 und 2020 entwickelt?"
    }

    results = {}

    for qid, question in questions.items():
        success = test_question(question, qid)
        results[qid] = "✅ 成功" if success else "❌ 失败"

    # 汇总结果
    logger.info("\n" + "="*100)
    logger.info("测试结果汇总")
    logger.info("="*100)
    for qid, result in results.items():
        logger.info(f"{qid}: {result}")

    # 检查是否全部成功
    all_success = all("成功" in r for r in results.values())
    if all_success:
        logger.info("\n🎉 所有测试通过！报告生成Bug已修复！")
    else:
        logger.error("\n⚠️ 部分测试失败，请检查日志")


if __name__ == "__main__":
    main()
