#!/usr/bin/env python3
"""
对比有ReRank vs 无ReRank的检索质量差异
"""
import os
import json
from pathlib import Path
from datetime import datetime

def analyze_retrieval_quality(report_dir):
    """分析单个报告的检索质量"""
    analysis_file = Path(report_dir) / "analysis" / "retrieval_analysis.md"

    if not analysis_file.exists():
        return None

    content = analysis_file.read_text(encoding='utf-8')

    # 提取关键指标
    result = {
        "dir": report_dir,
        "timestamp": Path(report_dir).name.split('_')[-1],
        "total_docs": 0,
        "avg_score": 0.0,
        "max_score": 0.0,
        "min_score": 0.0,
        "score_distribution": {}
    }

    for line in content.split('\n'):
        if "总检索文档数:" in line:
            result["total_docs"] = int(line.split(':')[1].strip())
        elif "平均分:" in line:
            result["avg_score"] = float(line.split(':')[1].strip())
        elif "最高分:" in line:
            result["max_score"] = float(line.split(':')[1].strip())
        elif "最低分:" in line:
            result["min_score"] = float(line.split(':')[1].strip())

    return result

def compare_reports():
    """对比有ReRank和无ReRank的报告"""
    outputs_dir = Path("outputs")

    # 11月18日的报告（有ReRank）
    rerank_date = "20251118"
    # 今天的报告（无ReRank）
    no_rerank_date = datetime.now().strftime("%Y%m%d")

    comparison = {}

    for qid in range(1, 8):
        qname = f"Q{qid}"
        comparison[qname] = {
            "with_rerank": None,
            "without_rerank": None
        }

        # 查找有ReRank版本（11月18日）
        rerank_dirs = sorted(outputs_dir.glob(f"{qname}_{rerank_date}_*"),
                            key=lambda x: x.name, reverse=True)
        if rerank_dirs:
            comparison[qname]["with_rerank"] = analyze_retrieval_quality(rerank_dirs[0])

        # 查找无ReRank版本（今天）
        no_rerank_dirs = sorted(outputs_dir.glob(f"{qname}_{no_rerank_date}_*"),
                                key=lambda x: x.name, reverse=True)
        if no_rerank_dirs:
            comparison[qname]["without_rerank"] = analyze_retrieval_quality(no_rerank_dirs[0])

    return comparison

def print_comparison(comparison):
    """打印对比结果"""
    print("=" * 80)
    print("🔍 ReRank影响对比分析")
    print("=" * 80)
    print()

    for qname, data in comparison.items():
        print(f"\n{'=' * 60}")
        print(f"📊 {qname}")
        print(f"{'=' * 60}")

        with_rerank = data["with_rerank"]
        without_rerank = data["without_rerank"]

        if with_rerank and without_rerank:
            print(f"\n{'指标':<20} {'有ReRank':<15} {'无ReRank':<15} {'差异':<15}")
            print("-" * 65)

            # 文档数对比
            docs_diff = without_rerank["total_docs"] - with_rerank["total_docs"]
            print(f"{'总检索文档数':<20} {with_rerank['total_docs']:<15} "
                  f"{without_rerank['total_docs']:<15} {docs_diff:+d}")

            # 平均分对比
            avg_diff = without_rerank["avg_score"] - with_rerank["avg_score"]
            print(f"{'平均相似度':<20} {with_rerank['avg_score']:<15.4f} "
                  f"{without_rerank['avg_score']:<15.4f} {avg_diff:+.4f}")

            # 最高分对比
            max_diff = without_rerank["max_score"] - with_rerank["max_score"]
            print(f"{'最高分':<20} {with_rerank['max_score']:<15.4f} "
                  f"{without_rerank['max_score']:<15.4f} {max_diff:+.4f}")

            # 最低分对比
            min_diff = without_rerank["min_score"] - with_rerank["min_score"]
            print(f"{'最低分':<20} {with_rerank['min_score']:<15.4f} "
                  f"{without_rerank['min_score']:<15.4f} {min_diff:+.4f}")

            # 结论
            print(f"\n💡 结论:")
            if avg_diff > 0.01:
                print("   ✅ 无ReRank版本平均相似度更高")
            elif avg_diff < -0.01:
                print("   ⚠️ 无ReRank版本平均相似度下降")
            else:
                print("   ➡️ 平均相似度变化不大")

        elif without_rerank and not with_rerank:
            print(f"⚠️ 只有无ReRank版本数据")
            print(f"   总检索文档数: {without_rerank['total_docs']}")
            print(f"   平均相似度: {without_rerank['avg_score']:.4f}")
        elif with_rerank and not without_rerank:
            print(f"⏳ 无ReRank版本测试尚未完成")
        else:
            print(f"❌ 两个版本的数据都不存在")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    comparison = compare_reports()
    print_comparison(comparison)
