"""
简单的Q6测试 - 验证Phase 4 Query扩展
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from test_langgraph_complete import create_pinecone_workflow, test_one_question
from src.utils.logger import logger

# Q6问题（匹配test_one_question的数据结构）
Q6_QUESTION = {
    "id": 6,
    "question": "Wie haben sich die Positionen der CDU/CSU zur Migrationspolitik zwischen 2017 und 2019 im Vergleich verändert?",
    "type": "离散年份对比",
    "years": "2017, 2019",
    "expected_years": [2017, 2019]
}

# Phase 4验证关键短语
EXPECTED_KEYWORDS = ["Zwang durchsetzen", "Ausreisegewahrsam", "Abschiebung"]

if __name__ == "__main__":
    print("=" * 100)
    print("🧪 Phase 4 Query扩展验证 - Q6单独测试")
    print("=" * 100)
    print()

    # 创建workflow
    logger.info("创建Pinecone工作流...")
    workflow = create_pinecone_workflow()

    # 运行Q6测试
    print(f"📝 测试问题: {Q6_QUESTION['question']}")
    print()

    result = test_one_question(workflow, Q6_QUESTION, total_questions=1)

    print()
    print("=" * 100)
    print("📊 Phase 4验证结果")
    print("=" * 100)

    if result:
        print("✅ Q6测试完成")
        print(f"📁 报告目录: {result.get('output_dir', 'Unknown')}")

        # 检查关键短语（Phase 4验证目标）
        final_answer = result.get('final_answer', '')
        print("\n🔍 Phase 4关键短语检查:")
        for keyword in EXPECTED_KEYWORDS:
            if keyword in final_answer:
                print(f"   ✅ {keyword}: 找到")
            else:
                print(f"   ❌ {keyword}: 缺失")

        # 检查关键文档是否被召回
        print("\n🔍 关键文档召回检查:")
        retrieval_thinking = result.get('retrieval_thinking', '')
        target_doc_id = "2017_1762423575_2922"
        if target_doc_id in retrieval_thinking:
            print(f"   ✅ 目标文档 {target_doc_id} 已被召回")
        else:
            print(f"   ❌ 目标文档 {target_doc_id} 未被召回")
    else:
        print("❌ Q6测试失败")
