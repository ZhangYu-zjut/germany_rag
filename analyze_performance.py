#!/usr/bin/env python3
"""
从test_AFTER_QUELLEN_FIX.log中提取性能数据
分析耗时分布和优化机会
"""
import re
from pathlib import Path
from collections import defaultdict

def extract_performance_data(log_file):
    """提取性能数据"""
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除ANSI颜色码
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    content = ansi_escape.sub('', content)

    results = []

    # 按问题分割
    questions = re.split(r'={40,}', content)

    for q_section in questions:
        if not q_section.strip():
            continue

        # 提取问题
        q_match = re.search(r'原始问题[:：]\s*(.+)', q_section)
        if not q_match:
            continue

        question = q_match.group(1).strip()

        # 提取各阶段耗时
        timings = {}

        # 检索耗时
        retrieve_match = re.search(r'检索耗时[:：]\s*([\d.]+)\s*秒', q_section)
        if retrieve_match:
            timings['retrieve'] = float(retrieve_match.group(1))

        # 重排序耗时
        rerank_match = re.search(r'重排序耗时[:：]\s*([\d.]+)\s*秒', q_section)
        if rerank_match:
            timings['rerank'] = float(rerank_match.group(1))

        # 总结耗时
        summarize_match = re.search(r'总结耗时[:：]\s*([\d.]+)\s*秒', q_section)
        if summarize_match:
            timings['summarize'] = float(summarize_match.group(1))

        # 总耗时
        total_match = re.search(r'总耗时[:：]\s*([\d.]+)\s*秒', q_section)
        if total_match:
            timings['total'] = float(total_match.group(1))

        # 提取检索方法
        retrieval_method = None
        method_match = re.search(r'检索方法[:：]\s*(.+)', q_section)
        if method_match:
            retrieval_method = method_match.group(1).strip()

        # 提取子问题数
        subq_count = 0
        subq_match = re.search(r'生成了\s*(\d+)\s*个子问题', q_section)
        if subq_match:
            subq_count = int(subq_match.group(1))

        # 提取检索到的文档数
        doc_count = 0
        doc_match = re.search(r'检索到\s*(\d+)\s*个相关文档', q_section)
        if doc_match:
            doc_count = int(doc_match.group(1))

        # 提取LLM调用信息 (通过搜索gemini-2.5-pro日志)
        llm_calls = len(re.findall(r'gemini-2\.5-pro', q_section))

        # 提取答案长度
        answer_len = 0
        answer_match = re.search(r'答案长度[:：]\s*(\d+)', q_section)
        if answer_match:
            answer_len = int(answer_match.group(1))

        results.append({
            'question': question,
            'timings': timings,
            'retrieval_method': retrieval_method,
            'subquestion_count': subq_count,
            'doc_count': doc_count,
            'llm_calls': llm_calls,
            'answer_length': answer_len
        })

    return results

def analyze_and_report(results):
    """分析并生成报告"""
    print("=" * 80)
    print("性能分析报告 - test_AFTER_QUELLEN_FIX.log")
    print("=" * 80)
    print()

    # 1. 总览表格
    print("## 1. 问题耗时总览")
    print()
    print("| # | 问题 | 检索(秒) | 重排(秒) | 总结(秒) | 总耗时(秒) | 子问题 | 文档数 |")
    print("|---|------|----------|----------|----------|------------|--------|--------|")

    for i, r in enumerate(results, 1):
        t = r['timings']
        q = r['question'][:50] + "..." if len(r['question']) > 50 else r['question']
        print(f"| {i} | {q} | {t.get('retrieve', 0):.2f} | {t.get('rerank', 0):.2f} | "
              f"{t.get('summarize', 0):.2f} | {t.get('total', 0):.2f} | "
              f"{r['subquestion_count']} | {r['doc_count']} |")

    print()
    print("-" * 80)
    print()

    # 2. 耗时分布分析
    print("## 2. 耗时分布分析")
    print()

    retrieve_times = [r['timings'].get('retrieve', 0) for r in results]
    rerank_times = [r['timings'].get('rerank', 0) for r in results]
    summarize_times = [r['timings'].get('summarize', 0) for r in results]
    total_times = [r['timings'].get('total', 0) for r in results]

    print(f"检索阶段:")
    print(f"  平均: {sum(retrieve_times)/len(retrieve_times):.2f}秒")
    print(f"  最小: {min(retrieve_times):.2f}秒")
    print(f"  最大: {max(retrieve_times):.2f}秒")
    print(f"  总计: {sum(retrieve_times):.2f}秒 ({sum(retrieve_times)/sum(total_times)*100:.1f}%)")
    print()

    print(f"重排序阶段:")
    print(f"  平均: {sum(rerank_times)/len(rerank_times):.2f}秒")
    print(f"  最小: {min(rerank_times):.2f}秒")
    print(f"  最大: {max(rerank_times):.2f}秒")
    print(f"  总计: {sum(rerank_times):.2f}秒 ({sum(rerank_times)/sum(total_times)*100:.1f}%)")
    print()

    print(f"总结阶段:")
    print(f"  平均: {sum(summarize_times)/len(summarize_times):.2f}秒")
    print(f"  最小: {min(summarize_times):.2f}秒")
    print(f"  最大: {max(summarize_times):.2f}秒")
    print(f"  总计: {sum(summarize_times):.2f}秒 ({sum(summarize_times)/sum(total_times)*100:.1f}%)")
    print()

    print(f"总耗时:")
    print(f"  平均: {sum(total_times)/len(total_times):.2f}秒")
    print(f"  总计: {sum(total_times):.2f}秒")
    print()

    # 3. 识别性能瓶颈
    print("-" * 80)
    print()
    print("## 3. 性能瓶颈识别")
    print()

    # 找出最慢的问题
    slowest = sorted(results, key=lambda x: x['timings'].get('total', 0), reverse=True)[:3]
    print("### 最慢的3个问题:")
    print()
    for i, r in enumerate(slowest, 1):
        t = r['timings']
        print(f"{i}. 总耗时: {t.get('total', 0):.2f}秒")
        print(f"   问题: {r['question']}")
        print(f"   检索: {t.get('retrieve', 0):.2f}秒 ({t.get('retrieve', 0)/t.get('total', 1)*100:.1f}%)")
        print(f"   重排: {t.get('rerank', 0):.2f}秒 ({t.get('rerank', 0)/t.get('total', 1)*100:.1f}%)")
        print(f"   总结: {t.get('summarize', 0):.2f}秒 ({t.get('summarize', 0)/t.get('total', 1)*100:.1f}%)")
        print(f"   子问题数: {r['subquestion_count']}")
        print(f"   检索方法: {r['retrieval_method']}")
        print()

    print("-" * 80)
    print()

    # 4. 子问题与耗时相关性
    print("## 4. 子问题数量与耗时相关性")
    print()
    for r in results:
        if r['subquestion_count'] > 0:
            avg_per_subq = r['timings'].get('retrieve', 0) / r['subquestion_count']
            print(f"问题: {r['question'][:60]}...")
            print(f"  子问题: {r['subquestion_count']}个, 检索耗时: {r['timings'].get('retrieve', 0):.2f}秒, "
                  f"平均每个子问题: {avg_per_subq:.2f}秒")
            print()

    return results

if __name__ == "__main__":
    log_file = Path("11-07测试结果/test_AFTER_QUELLEN_FIX.log")

    if not log_file.exists():
        print(f"错误: 找不到日志文件 {log_file}")
        exit(1)

    print("正在分析日志文件...")
    print()

    results = extract_performance_data(log_file)

    if not results:
        print("警告: 未能提取到性能数据")
        exit(1)

    print(f"成功提取 {len(results)} 个问题的性能数据")
    print()

    analyze_and_report(results)
