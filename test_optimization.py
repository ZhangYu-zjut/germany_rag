#!/usr/bin/env python3
"""
测试并行化和模型切换优化效果
对比优化前后的性能和答案质量
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger

logger = setup_logger()

# 测试问题 - 选择最慢的Q1和中等速度的Q4
TEST_QUESTIONS = [
    {
        "id": 1,
        "question": "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化。",
        "type": "多年变化(2015-2024)",
        "baseline_time": 1145.59,  # 优化前的耗时
        "expected_speedup": "10-20倍"
    },
    {
        "id": 4,
        "question": "在2015年到2018年期间，德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化？",
        "type": "跨年变化(2015-2018)",
        "baseline_time": 416.34,
        "expected_speedup": "5-10倍"
    }
]

def test_optimized_workflow():
    """测试优化后的workflow"""
    from src.graph.workflow import QuestionAnswerWorkflow

    print("=" * 80)
    print("RAG系统性能优化验证测试")
    print("=" * 80)
    print()
    print("优化内容:")
    print("  1. ✅ 并行化Retrieve - search_multi_year_parallel()")
    print("  2. ✅ 分层模型选择 - Intent/Classify/Extract使用Gemini 2.5 Flash")
    print()
    print("预期效果:")
    print("  - Q1: 1145秒 → 60-120秒 (10-20倍加速)")
    print("  - Q4: 416秒 → 40-80秒 (5-10倍加速)")
    print()
    print("-" * 80)
    print()

    # 创建workflow
    logger.info("创建优化后的RAG工作流...")
    workflow = QuestionAnswerWorkflow()
    app = workflow.graph

    results = []

    for q in TEST_QUESTIONS:
        print(f"\n{'='*80}")
        print(f"问题 {q['id']}: {q['type']}")
        print(f"{'='*80}")
        print(f"问题: {q['question']}")
        print(f"优化前耗时: {q['baseline_time']:.2f}秒")
        print(f"预期加速: {q['expected_speedup']}")
        print()

        # 记录开始时间
        start_time = time.time()

        try:
            # 执行workflow
            final_state = None
            node_times = {}
            node_start = start_time

            for state in app.stream({"question": q['question']}):
                if "__end__" not in state:
                    node_name = list(state.keys())[0]
                    node_end = time.time()
                    node_times[node_name] = node_end - node_start
                    node_start = node_end

                    # 打印节点进度
                    print(f"  ✓ {node_name}: {node_times[node_name]:.2f}秒")

                final_state = state

            # 记录总耗时
            end_time = time.time()
            total_time = end_time - start_time

            # 提取结果
            if "__end__" in final_state:
                answer = final_state["__end__"].get("answer", "")
                answer_length = len(answer)

                # 计算加速比
                speedup = q['baseline_time'] / total_time

                print()
                print(f"✅ 问题 {q['id']} 完成")
                print(f"  总耗时: {total_time:.2f}秒")
                print(f"  加速比: {speedup:.1f}x (优化前: {q['baseline_time']:.2f}秒)")
                print(f"  答案长度: {answer_length}字符")
                print()

                # 验证答案是否包含Quellen
                has_quellen = "**Quellen**" in answer or "Quellen:" in answer
                print(f"  Quellen格式: {'✅ 包含' if has_quellen else '❌ 缺失'}")

                # 节点耗时分解
                print()
                print("  节点耗时分解:")
                for node, t in node_times.items():
                    percentage = (t / total_time) * 100
                    print(f"    {node}: {t:.2f}秒 ({percentage:.1f}%)")

                results.append({
                    "question_id": q['id'],
                    "question": q['question'],
                    "baseline_time": q['baseline_time'],
                    "optimized_time": total_time,
                    "speedup": speedup,
                    "answer_length": answer_length,
                    "has_quellen": has_quellen,
                    "node_times": node_times
                })

            else:
                print(f"⚠️  未能获取最终状态")

        except Exception as e:
            print(f"❌ 问题 {q['id']} 执行失败: {str(e)}")
            import traceback
            traceback.print_exc()

    # 生成总结报告
    print()
    print("=" * 80)
    print("优化效果总结")
    print("=" * 80)
    print()

    if results:
        total_baseline = sum(r['baseline_time'] for r in results)
        total_optimized = sum(r['optimized_time'] for r in results)
        avg_speedup = sum(r['speedup'] for r in results) / len(results)

        print(f"测试问题数: {len(results)}")
        print(f"总耗时(优化前): {total_baseline:.2f}秒 ({total_baseline/60:.1f}分钟)")
        print(f"总耗时(优化后): {total_optimized:.2f}秒 ({total_optimized/60:.1f}分钟)")
        print(f"总节省时间: {total_baseline - total_optimized:.2f}秒 ({(total_baseline - total_optimized)/60:.1f}分钟)")
        print(f"平均加速比: {avg_speedup:.1f}x")
        print()

        print("各问题详情:")
        for r in results:
            print(f"  Q{r['question_id']}: {r['baseline_time']:.0f}秒 → {r['optimized_time']:.0f}秒 "
                  f"({r['speedup']:.1f}x加速, {'✅' if r['has_quellen'] else '❌'}Quellen)")

        print()
        print("优化评估:")
        if avg_speedup >= 8:
            print("  🎉 优化非常成功! 达到预期目标")
        elif avg_speedup >= 5:
            print("  ✅ 优化效果良好, 接近预期目标")
        elif avg_speedup >= 3:
            print("  ⚠️  有一定优化效果, 但低于预期")
        else:
            print("  ❌ 优化效果不明显, 需要检查")

        # 检查答案质量
        all_have_quellen = all(r['has_quellen'] for r in results)
        print()
        print("答案质量:")
        if all_have_quellen:
            print("  ✅ 所有答案都包含Quellen格式")
        else:
            print("  ⚠️  部分答案缺少Quellen格式")

    print()
    print("=" * 80)

    return results

if __name__ == "__main__":
    results = test_optimized_workflow()
