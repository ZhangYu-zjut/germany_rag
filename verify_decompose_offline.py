#!/usr/bin/env python3
"""
离线验证Decompose模板改进（方案A）
无需调用LLM，直接测试主题扩展逻辑
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.graph.templates.decompose_templates import ChangeAnalysisTemplate

def test_q6_decompose():
    """测试Q6问题的Decompose逻辑"""

    print("=" * 80)
    print("🧪 Phase 4方案A离线验证：Decompose主题扩展")
    print("=" * 80)
    print()

    # 模拟Q6的Extract节点输出
    q6_parameters = {
        "time_range": {
            "start_year": "2017",
            "end_year": "2019",
            "specific_years": ["2017", "2019"]  # 离散年份
        },
        "parties": ["CDU/CSU"],
        "topics": ["Migrationspolitik"]  # ← 抽象主题！
    }

    print("📝 模拟输入（Extract节点输出）:")
    print(f"   党派: {q6_parameters['parties']}")
    print(f"   主题: {q6_parameters['topics']}")
    print(f"   年份: {q6_parameters['time_range']['specific_years']}")
    print()

    # 创建模板
    template = ChangeAnalysisTemplate()

    # 检测抽象主题
    topic_str = ", ".join(q6_parameters['topics'])
    is_abstract = template._is_abstract_topic(topic_str)

    print("🔍 抽象主题检测:")
    print(f"   主题: {topic_str}")
    print(f"   是否抽象: {'✅ 是' if is_abstract else '❌ 否'}")
    print()

    if is_abstract:
        # 获取扩展维度
        dimensions = template._expand_topic_dimensions(topic_str)
        print("📊 主题扩展维度:")
        for i, dim in enumerate(dimensions, 1):
            print(f"   {i}. {dim}")
        print()

    # 生成子问题
    sub_questions = template.generate_sub_questions(q6_parameters)

    print("=" * 80)
    print("📋 生成的子问题列表")
    print("=" * 80)
    print(f"总计: {len(sub_questions)} 个子问题")
    print()

    # 检查关键词出现
    keywords_to_check = ["Abschiebung", "Rückführung", "Zwang"]
    keyword_found = {kw: False for kw in keywords_to_check}

    for i, sub_q in enumerate(sub_questions, 1):
        question_text = sub_q.get("question", "")
        target_year = sub_q.get("target_year", "N/A")
        dimension = sub_q.get("topic_dimension", "N/A")

        print(f"子问题 {i}:")
        print(f"   年份: {target_year}")
        print(f"   维度: {dimension}")
        print(f"   查询: {question_text}")

        # 检查关键词
        for kw in keywords_to_check:
            if kw in question_text:
                keyword_found[kw] = True
                print(f"   ✅ 包含关键词: {kw}")

        print()

    # 验证结果
    print("=" * 80)
    print("🎯 验证结果")
    print("=" * 80)
    print()

    print("【关键词检查】:")
    all_found = True
    for kw, found in keyword_found.items():
        status = "✅ 找到" if found else "❌ 缺失"
        print(f"   {kw}: {status}")
        if not found:
            all_found = False
    print()

    print("【预期行为】:")
    expected_count = len(q6_parameters['time_range']['specific_years']) * len(template.topic_expansion_map.get("Migrationspolitik", []))
    actual_count = len(sub_questions)

    print(f"   预期子问题数: {expected_count} (2年 × 4维度)")
    print(f"   实际子问题数: {actual_count}")
    count_match = (expected_count == actual_count)
    print(f"   数量匹配: {'✅ 是' if count_match else '❌ 否'}")
    print()

    # 检查是否包含"Abschiebung"维度的查询
    abschiebung_queries = [
        q for q in sub_questions
        if "Abschiebung" in q.get("question", "")
    ]

    print("【核心验证：Abschiebung查询】:")
    print(f"   包含'Abschiebung'的查询数: {len(abschiebung_queries)}")

    if abschiebung_queries:
        print("   ✅ 验证成功！生成了包含'Abschiebung'的查询")
        print()
        print("   示例查询:")
        for q in abschiebung_queries[:2]:
            print(f"   - {q.get('question', '')}")
    else:
        print("   ❌ 验证失败！未生成包含'Abschiebung'的查询")

    print()
    print("=" * 80)
    print("📊 总结")
    print("=" * 80)

    success = all_found and count_match and len(abschiebung_queries) > 0

    if success:
        print("✅✅✅ 方案A代码逻辑验证通过！")
        print()
        print("【理论召回分析】:")
        print("   1. ✅ 查询包含'Abschiebung'关键词")
        print("   2. ✅ 目标文档包含'Zwang durchsetzen'（强制遣返）")
        print("   3. ✅ BGE-M3能理解'Abschiebung'和'Zwang durchsetzen'的语义关联")
        print("   4. ✅ 预计能成功召回目标文档 2017_1762423575_2922")
        print()
        print("【下一步】:")
        print("   等待LLM API恢复后，运行完整测试验证实际召回效果")
    else:
        print("❌ 方案A代码逻辑存在问题，需要修复")
        print()
        print("【问题】:")
        if not all_found:
            print("   - 未生成包含所有必要关键词的查询")
        if not count_match:
            print("   - 子问题数量不符合预期")
        if len(abschiebung_queries) == 0:
            print("   - 未生成包含'Abschiebung'的查询（致命！）")

    return success

if __name__ == "__main__":
    success = test_q6_decompose()
    sys.exit(0 if success else 1)
