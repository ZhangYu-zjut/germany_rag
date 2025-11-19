#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/zhangyu/project/rag_germant')

from test_langgraph_complete import *

# 只测试Q4-Q7
TEST_QUESTIONS_Q4567 = [
    TEST_QUESTIONS_DE[3],  # Q4
    TEST_QUESTIONS_DE[4],  # Q5
    TEST_QUESTIONS_DE[5],  # Q6
    TEST_QUESTIONS_DE[6],  # Q7
]

if __name__ == "__main__":
    logger.info("="*100)
    logger.info("🚀 运行Q4-Q7测试")
    logger.info("="*100)

    # 创建workflow
    logger.info("\n📦 1. 创建Pinecone优化版工作流")
    logger.info("-"*100)
    workflow = create_pinecone_workflow()
    logger.info("✅ 工作流创建完成\n")

    # 运行Q4-Q7
    logger.info("\n📋 2. 运行Q4-Q7测试")
    logger.info("-"*100)

    for i, question_data in enumerate(TEST_QUESTIONS_Q4567, 1):
        result = test_one_question(workflow, question_data, total_questions=4)
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ 问题 {i}/4 完成")
        logger.info(f"报告目录: {result.get('report_dir', 'N/A')}")
        logger.info(f"{'='*80}\n")

    logger.info("\n✅ Q4-Q7测试全部完成!")
