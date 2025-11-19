#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/zhangyu/project/rag_germant')

from test_langgraph_complete import *

# 只测试Q1-Q3
TEST_QUESTIONS_Q123 = [
    TEST_QUESTIONS_DE[0],  # Q1
    TEST_QUESTIONS_DE[1],  # Q2
    TEST_QUESTIONS_DE[2],  # Q3
]

if __name__ == "__main__":
    logger.info("="*100)
    logger.info("🚀 运行Q1-Q3测试")
    logger.info("="*100)

    # 创建workflow
    logger.info("\n📦 1. 创建Pinecone优化版工作流")
    logger.info("-"*100)
    workflow = create_pinecone_workflow()
    logger.info("✅ 工作流创建完成\n")

    # 运行Q1-Q3
    logger.info("\n📋 2. 运行Q1-Q3测试")
    logger.info("-"*100)

    for i, question_data in enumerate(TEST_QUESTIONS_Q123, 1):
        result = test_one_question(workflow, question_data, total_questions=3)
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ 问题 {i}/3 完成")
        logger.info(f"报告目录: {result.get('report_dir', 'N/A')}")
        logger.info(f"{'='*80}\n")

    logger.info("\n✅ Q1-Q3测试全部完成!")
