"""
验证修复效果的针对性测试
只测试问题5和问题6
"""
import sys
import time
from src.graph.workflow import QuestionAnswerWorkflow
from src.utils.logger import logger

# 只测试这2个问题
TEST_QUESTIONS = [
    {
        "id": 5,
        "question": "请对比2015-2017年联盟党与绿党在移民融合政策方面的主张。",
        "expected_years": ["2015", "2016", "2017"],
        "bug_description": "原问题：只生成2015年的子问题"
    },
    {
        "id": 6,
        "question": "2019年与2017年相比，联邦议会关于难民遣返的讨论有何变化？",
        "expected_years": ["2017", "2019"],
        "bug_description": "原问题：提取了[2017, 2018, 2019]，应该只有2017和2019"
    }
]

def test_question(workflow, test_case: dict) -> bool:
    """
    测试单个问题

    Returns:
        修复是否成功
    """
    question = test_case["question"]
    expected_years = test_case["expected_years"]
    q_id = test_case["id"]

    print(f"\n{'='*70}")
    print(f"📝 测试问题 {q_id}")
    print(f"{'='*70}")
    print(f"问题: {question}")
    print(f"期望年份: {expected_years}")
    print(f"原bug: {test_case['bug_description']}")
    print()

    start_time = time.time()

    try:
        # 执行workflow
        result = workflow.run(question, verbose=False, enable_performance_monitor=False)

        elapsed = time.time() - start_time

        # 提取参数和子问题
        parameters = result.get("parameters", {})
        sub_questions = result.get("sub_questions", [])

        # 验证1: 参数提取
        time_range = parameters.get("time_range", {})
        specific_years = time_range.get("specific_years", [])

        print("="*70)
        print("📊 验证结果")
        print("="*70)
        print(f"⏱️  耗时: {elapsed:.1f}秒")
        print()

        # 检查参数提取
        print("【参数提取验证】")
        print(f"  提取的年份: {specific_years}")
        print(f"  期望年份: {expected_years}")

        years_correct = set(specific_years) == set(expected_years)
        if years_correct:
            print(f"  ✅ 年份提取正确")
        else:
            print(f"  ❌ 年份提取错误")
            print(f"     多余: {set(specific_years) - set(expected_years)}")
            print(f"     缺少: {set(expected_years) - set(specific_years)}")

        print()

        # 检查子问题拆解
        print("【子问题拆解验证】")
        print(f"  生成子问题数: {len(sub_questions)}")

        if sub_questions:
            # 检查子问题中是否包含所有期望年份
            sub_q_text = " ".join(sub_questions)
            years_in_sub_q = [year for year in expected_years if year in sub_q_text]

            print(f"  子问题中出现的年份: {years_in_sub_q}")

            decompose_correct = len(years_in_sub_q) == len(expected_years)
            if decompose_correct:
                print(f"  ✅ 子问题拆解正确，包含所有期望年份")
            else:
                print(f"  ❌ 子问题拆解不完整")
                print(f"     缺少年份: {set(expected_years) - set(years_in_sub_q)}")

            # 打印子问题（用于人工验证）
            print()
            print("  生成的子问题:")
            for i, sq in enumerate(sub_questions[:5], 1):  # 只显示前5个
                print(f"    {i}. {sq}")
            if len(sub_questions) > 5:
                print(f"    ... (共{len(sub_questions)}个)")
        else:
            print(f"  ❌ 未生成子问题")
            decompose_correct = False

        print()
        print("="*70)

        # 综合判断
        success = years_correct and decompose_correct

        if success:
            print(f"✅ 问题 {q_id} 修复验证成功！")
        else:
            print(f"❌ 问题 {q_id} 修复验证失败")

        print("="*70)

        return success

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"测试问题 {q_id} 失败: {str(e)}")
        import traceback
        print(f"\n❌ 异常: {str(e)}")
        print(traceback.format_exc())
        print(f"⏱️  耗时: {elapsed:.1f}秒")
        return False


def main():
    """主测试函数"""
    print("="*70)
    print("修复效果验证测试")
    print("="*70)
    print()
    print("测试内容:")
    print("  - 问题5: ComparisonTemplate时间范围修复")
    print("  - 问题6: Extract年份展开逻辑修复")
    print()
    print(f"测试问题数: {len(TEST_QUESTIONS)}")
    print()

    # 创建workflow
    print("初始化RAG workflow...")
    workflow = QuestionAnswerWorkflow()
    print("✅ Workflow初始化完成")
    print()

    # 执行测试
    results = []
    for test_case in TEST_QUESTIONS:
        success = test_question(workflow, test_case)
        results.append({
            "id": test_case["id"],
            "question": test_case["question"],
            "success": success
        })

        # 问题间暂停
        if test_case != TEST_QUESTIONS[-1]:
            print("\n⏸️  等待3秒后继续...\n")
            time.sleep(3)

    # 生成总结报告
    print("\n" + "="*70)
    print("📊 验证总结")
    print("="*70)
    print()

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    print(f"成功: {success_count}/{total_count}")
    print()

    if success_count == total_count:
        print("🎉 所有修复验证通过！")
        print()
        print("建议:")
        print("  ✅ 修复有效，可以进行完整的7问题测试")
        return 0
    else:
        print("⚠️ 部分修复验证失败")
        print()
        print("失败的问题:")
        for r in results:
            if not r["success"]:
                print(f"  ❌ 问题{r['id']}: {r['question'][:50]}...")
        print()
        print("建议:")
        print("  1. 检查修复代码")
        print("  2. 查看详细日志")
        print("  3. 修复后重新测试")
        return 1


if __name__ == "__main__":
    sys.exit(main())
