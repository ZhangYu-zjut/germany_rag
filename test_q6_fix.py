#!/usr/bin/env python3
"""
测试Q6年份过滤修复
验证 "2019年与2017年相比" 只检索2017和2019年的数据，不包含2018年
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.graph.workflow import QuestionAnswerWorkflow
from src.utils.logger import logger

def test_q6_year_filtering():
    """测试Q6的离散年份对比"""

    print("=" * 80)
    print("Q6年份过滤修复验证测试")
    print("=" * 80)
    print()

    # Q6原问题
    question = "2019年与2017年相比，联邦议会关于难民遣返的讨论有何变化？"

    print(f"📝 测试问题: {question}")
    print()
    print("✅ 预期行为:")
    print("   - Extract阶段: specific_years=['2017', '2019']")
    print("   - Retrieve阶段: 只检索2017和2019年的数据")
    print("   - 年份分布: {'2017': X, '2019': Y} (不包含2018)")
    print()
    print("❌ 修复前的错误行为:")
    print("   - Retrieve阶段: 使用range(2017, 2020)扩展为['2017', '2018', '2019']")
    print("   - 年份分布: {'2017': 5, '2018': 5, '2019': 5}")
    print()
    print("-" * 80)
    print()

    # 创建工作流
    logger.info("创建RAG工作流...")
    workflow = QuestionAnswerWorkflow()
    app = workflow.build()

    # 执行问答
    logger.info(f"开始处理问题: {question}")

    try:
        # 运行工作流
        final_state = None
        for state in app.stream({"question": question}):
            final_state = state

            # 检查Retrieve节点的输出
            if "__end__" not in state:
                node_name = list(state.keys())[0]
                node_state = state[node_name]

                # 重点关注Extract和Retrieve节点
                if node_name == "extract":
                    parameters = node_state.get("parameters", {})
                    time_range = parameters.get("time_range", {})
                    print("\n🔍 Extract阶段输出:")
                    print(f"   start_year: {time_range.get('start_year')}")
                    print(f"   end_year: {time_range.get('end_year')}")
                    print(f"   specific_years: {time_range.get('specific_years')}")
                    print()

                if node_name == "retrieve":
                    retrieval_results = node_state.get("retrieval_results", [])
                    overall_year_dist = node_state.get("overall_year_distribution", {})

                    print("\n🔍 Retrieve阶段输出:")
                    print(f"   检索到的子问题数: {len(retrieval_results)}")

                    for i, result in enumerate(retrieval_results, 1):
                        print(f"\n   子问题 {i}:")
                        print(f"      问题: {result['question']}")
                        print(f"      检索到的文档数: {len(result['chunks'])}")
                        print(f"      年份分布: {result['year_distribution']}")
                        print(f"      检索方法: {result['retrieval_method']}")

                    print(f"\n   整体年份分布: {overall_year_dist}")
                    print()

                    # 验证年份分布
                    print("-" * 80)
                    print("\n✅ 验证结果:")

                    years_found = set(overall_year_dist.keys())
                    expected_years = {'2017', '2019'}

                    if '2018' in years_found:
                        print("   ❌ 失败: 检索结果中包含2018年数据！")
                        print(f"   发现的年份: {years_found}")
                        print("   修复未生效，Retrieve阶段仍在使用range逻辑")
                        return False
                    elif years_found == expected_years:
                        print("   ✅ 成功: 只检索了2017和2019年的数据")
                        print(f"   发现的年份: {years_found}")
                        print("   修复生效！specific_years优先级正确")
                        return True
                    elif years_found.issubset(expected_years) and len(years_found) > 0:
                        print("   ⚠️  部分成功: 检索了预期年份的子集")
                        print(f"   发现的年份: {years_found}")
                        print(f"   缺失的年份: {expected_years - years_found}")
                        return True
                    else:
                        print(f"   ⚠️  意外结果: {years_found}")
                        print(f"   预期: {expected_years}")
                        return False

        # 如果没有触发Retrieve节点的检查（不应该发生）
        print("\n⚠️  警告: 未能检测到Retrieve节点输出")
        return None

    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    result = test_q6_year_filtering()
    print()
    print("=" * 80)

    if result is True:
        print("🎉 测试通过！Q6年份过滤修复成功")
        print()
        print("修复要点:")
        print("  1. _extract_filters()中优先检查specific_years")
        print("  2. 只在没有specific_years时才使用start_year/end_year范围逻辑")
        print("  3. 离散对比问题（如'2019年与2017年相比'）现在正确处理")
    elif result is False:
        print("❌ 测试失败！Q6年份过滤仍有问题")
        print()
        print("需要检查:")
        print("  1. retrieve_pinecone.py的_extract_filters()方法是否正确修改")
        print("  2. 是否有缓存导致旧代码仍在运行")
        print("  3. Extract阶段是否正确提取了specific_years")
    else:
        print("⚠️  测试结果不确定，请查看上方日志")

    print("=" * 80)
    print()
