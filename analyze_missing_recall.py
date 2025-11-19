#!/usr/bin/env python3
"""
分析Q1的9处遗漏text_id在检索/ReRank/总结各阶段的召回情况
"""
import os
import json
from pathlib import Path

# Q1的9处遗漏text_id（来自反馈文件）
MISSING_TEXT_IDS = [
    # 2015年遗漏
    "2015_1762361835_5700",
    "2015_1762417259_15318",
    "2015_1762361835_7866",
    # 2016年遗漏
    "2016_1762423144_4894",
    # 2017年遗漏（4处）
    "2017_1762423575_7519",
    "2017_1762423575_7522",
    "2017_1762423575_7461",
    "2017_1762423575_2922",
    # 2018年遗漏
    "2018_1762424261_1426",
    # 2018年第2处遗漏
    "2018_1762424261_12252",
    # 2019-2020遗漏
    "2019_1762425176_20492",
    "2020_1762425980_5052",
    # 2021-2024遗漏
    "2022_1762426486_1154",
    "2022_1762426486_4020",
    "2024_1762427428_7052"
]

def analyze_q1_output_dir(output_dir):
    """分析一个Q1输出目录"""
    print(f"\n{'='*80}")
    print(f"分析输出目录: {output_dir}")
    print(f"{'='*80}\n")

    # 1. 检查retrieval_analysis.md - 检索召回情况
    retrieval_file = Path(output_dir) / "analysis" / "retrieval_analysis.md"
    if retrieval_file.exists():
        print("📊 检索召回分析:")
        content = retrieval_file.read_text(encoding='utf-8')

        for text_id in MISSING_TEXT_IDS:
            if text_id in content:
                # 提取排名信息
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if text_id in line:
                        print(f"  ✅ {text_id}: 在检索结果中")
                        # 尝试找到排名
                        if "Rank #" in line or "排名" in line:
                            print(f"     {line.strip()}")
                        break
            else:
                print(f"  ❌ {text_id}: 未被检索召回")

    # 2. 检查citation_mapping.md - 最终引用情况
    citation_file = Path(output_dir) / "analysis" / "citation_mapping.md"
    if citation_file.exists():
        print("\n📝 最终引用分析:")
        content = citation_file.read_text(encoding='utf-8')

        for text_id in MISSING_TEXT_IDS:
            if text_id in content:
                print(f"  ✅ {text_id}: 在最终报告中被引用")
            else:
                print(f"  ❌ {text_id}: 未在最终报告中引用")

    # 3. 统计
    print("\n📈 统计摘要:")
    if retrieval_file.exists() and citation_file.exists():
        ret_content = retrieval_file.read_text(encoding='utf-8')
        cit_content = citation_file.read_text(encoding='utf-8')

        recalled = sum(1 for tid in MISSING_TEXT_IDS if tid in ret_content)
        cited = sum(1 for tid in MISSING_TEXT_IDS if tid in cit_content)

        print(f"  总共遗漏数: {len(MISSING_TEXT_IDS)}")
        print(f"  检索召回数: {recalled}/{len(MISSING_TEXT_IDS)} ({recalled/len(MISSING_TEXT_IDS)*100:.1f}%)")
        print(f"  最终引用数: {cited}/{len(MISSING_TEXT_IDS)} ({cited/len(MISSING_TEXT_IDS)*100:.1f}%)")
        print(f"  检索→引用损失: {recalled - cited}/{recalled} ({(recalled-cited)/recalled*100 if recalled > 0 else 0:.1f}%)")

        return {
            "total": len(MISSING_TEXT_IDS),
            "recalled": recalled,
            "cited": cited,
            "retrieval_loss": len(MISSING_TEXT_IDS) - recalled,
            "summarization_loss": recalled - cited
        }

    return None

if __name__ == "__main__":
    # 分析最新的Q1输出
    q1_dirs = sorted(Path("outputs").glob("Q1_20251118_*"), reverse=True)

    if not q1_dirs:
        print("❌ 未找到Q1输出目录")
        exit(1)

    results = []
    for q1_dir in q1_dirs[:1]:  # 只分析最新的
        result = analyze_q1_output_dir(q1_dir)
        if result:
            results.append(result)

    # 总结
    if results:
        print(f"\n{'='*80}")
        print("🎯 关键发现:")
        print(f"{'='*80}")

        result = results[0]
        retrieval_loss = result['retrieval_loss']
        summarization_loss = result['summarization_loss']

        print(f"\n1. 检索层损失: {retrieval_loss}/{result['total']} ({retrieval_loss/result['total']*100:.1f}%)")
        print(f"   → 这些文档根本没被召回到top 50")

        print(f"\n2. 总结层损失: {summarization_loss}/{result['recalled']} ({summarization_loss/result['recalled']*100 if result['recalled'] > 0 else 0:.1f}%)")
        print(f"   → 这些文档被召回了，但最终报告中未引用")

        if retrieval_loss > summarization_loss:
            print(f"\n⚠️ 结论: **检索层是主要瓶颈**")
            print(f"   需要优化: Query扩展、Embedding质量、检索策略")
        elif summarization_loss > retrieval_loss:
            print(f"\n⚠️ 结论: **总结层是主要瓶颈**")
            print(f"   需要优化: 总结策略、ReRank质量")
        else:
            print(f"\n⚠️ 结论: **检索层和总结层都有问题**")
            print(f"   需要同时优化两个层级")
