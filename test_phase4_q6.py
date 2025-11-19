"""
Phase 4测试：Query扩展方案验证
专门测试Q6问题，验证"Zwang durchsetzen"是否能被成功召回
"""

import os
import sys
from datetime import datetime

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.graph.workflow import create_graph
from src.utils.logger import logger


def test_q6_phase4():
    """测试Q6问题（Phase 4: Query扩展）"""

    print("=" * 80)
    print("🧪 Phase 4测试：Query扩展方案")
    print("=" * 80)
    print()

    # Q6问题
    question = "Wie haben sich die Positionen der CDU/CSU zur Migrationspolitik zwischen 2017 und 2019 im Vergleich verändert?"

    print(f"📝 测试问题: {question}")
    print()
    print("🎯 验证目标:")
    print("   1. Query扩展是否生效（应生成3个查询变体）")
    print("   2. 关键文档text_id 2017_1762423575_2922是否被召回")
    print("   3. 报告中是否出现'Zwang durchsetzen'短语")
    print()
    print("-" * 80)
    print()

    try:
        # 创建workflow
        graph = create_graph()

        # 运行
        logger.info(f"开始测试Q6...")
        result = graph.invoke({"question": question})

        # 提取报告
        final_answer = result.get("final_answer", "")
        retrieval_thinking = result.get("retrieval_thinking", "")
        retrieval_results = result.get("retrieval_results", [])

        print("\n" + "=" * 80)
        print("📊 检索阶段分析")
        print("=" * 80)

        # 检查1: Query扩展是否生效
        print("\n【检查1】Query扩展生效情况:")
        if "Query扩展" in retrieval_thinking:
            print("   ✅ Query扩展已启用")
            # 提取变体信息
            lines = retrieval_thinking.split('\n')
            for line in lines:
                if '变体' in line:
                    print(f"   {line}")
        else:
            print("   ❌ Query扩展未启用（可能代码未生效）")

        # 检查2: 关键文档是否被召回
        print("\n【检查2】关键文档召回情况:")
        target_text_id = "2017_1762423575_2922"
        found_target = False

        for sub_result in retrieval_results:
            chunks = sub_result.get("chunks", [])
            for i, chunk in enumerate(chunks):
                chunk_id = chunk.get("id", "")
                if target_text_id in chunk_id:
                    found_target = True
                    score = chunk.get("score", 0)
                    text_preview = chunk.get("text", "")[:150]
                    print(f"   ✅ 找到目标文档！")
                    print(f"      - 文档ID: {chunk_id}")
                    print(f"      - 相似度: {score:.4f}")
                    print(f"      - 排名: Top-{i+1}")
                    print(f"      - 内容预览: {text_preview}...")
                    break
            if found_target:
                break

        if not found_target:
            print(f"   ❌ 未找到目标文档 {target_text_id}")

        # 检查3: 报告中是否包含关键短语
        print("\n【检查3】报告内容检查:")
        key_phrases = [
            "Zwang durchsetzen",
            "强制执行",
            "Ausreisepflicht",
            "遣返义务"
        ]

        found_phrases = []
        for phrase in key_phrases:
            if phrase in final_answer:
                found_phrases.append(phrase)

        if found_phrases:
            print(f"   ✅ 报告中包含关键短语: {', '.join(found_phrases)}")
        else:
            print(f"   ❌ 报告中未包含任何关键短语")

        # 统计总召回文档数
        total_docs = sum(len(r.get("chunks", [])) for r in retrieval_results)
        print(f"\n【统计】总召回文档数: {total_docs}")

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"outputs/Q6_Phase4_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)

        report_path = os.path.join(output_dir, "Q6_full_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(final_answer)

        thinking_path = os.path.join(output_dir, "retrieval_thinking.txt")
        with open(thinking_path, 'w', encoding='utf-8') as f:
            f.write(retrieval_thinking)

        print(f"\n📁 报告已保存:")
        print(f"   - 完整报告: {report_path}")
        print(f"   - 检索思考: {thinking_path}")

        # 最终判断
        print("\n" + "=" * 80)
        print("🎯 Phase 4效果评估")
        print("=" * 80)

        if found_target and found_phrases:
            print("✅✅✅ Phase 4成功！关键文档已召回且报告包含关键短语")
            return True
        elif found_target:
            print("⚠️ Phase 4部分成功：文档已召回，但报告中缺失关键短语（可能是总结问题）")
            return False
        else:
            print("❌ Phase 4失败：关键文档未被召回（需要考虑方案A或BM25）")
            return False

    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_q6_phase4()
    sys.exit(0 if success else 1)
