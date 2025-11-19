#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/zhangyu/project/rag_germant')

from test_langgraph_complete import *

# 只测试Q1
TEST_QUESTIONS_Q1_ONLY = [TEST_QUESTIONS_DE[0]]

if __name__ == "__main__":
    logger.info("="*100)
    logger.info("🚀 测试Q1 (单独测试)")
    logger.info("="*100)
    
    # 创建workflow
    logger.info("\n📦 1. 创建Pinecone优化版工作流")
    logger.info("-"*100)
    workflow = create_pinecone_workflow()
    logger.info("✅ 工作流创建完成\n")
    
    # 只运行Q1
    logger.info("\n📋 2. 运行Q1测试")
    logger.info("-"*100)
    
    result = test_one_question(workflow, TEST_QUESTIONS_Q1_ONLY[0], total_questions=1)
    
    logger.info("\n✅ Q1测试完成!")
    logger.info(f"报告目录: {result.get('report_dir', 'N/A')}")
