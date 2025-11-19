#!/usr/bin/env python3
"""
新旧架构对比演示脚本
演示Q1在新旧架构下的效果差异
"""
import os
import json
from pathlib import Path
from datetime import datetime

# Q1的15个遗漏text_id（来自反馈文件）
MISSING_TEXT_IDS = [
    "2015_1762361835_5700",
    "2015_1762417259_15318",
    "2015_1762361835_7866",
    "2016_1762423144_4894",
    "2017_1762423575_7519",
    "2017_1762423575_7522",
    "2017_1762423575_7461",
    "2017_1762423575_2922",
    "2018_1762424261_1426",
    "2018_1762424261_12252",
    "2019_1762425176_20492",
    "2020_1762425980_5052",
    "2022_1762426486_1154",
    "2022_1762426486_4020",
    "2024_1762427428_7052"
]

def modify_env_config(enable_new_arch: bool):
    """修改.env配置，切换新旧架构"""
    env_file = Path(".env")

    if not env_file.exists():
        print("⚠️ .env文件不存在，请先创建")
        return

    content = env_file.read_text(encoding='utf-8')

    if enable_new_arch:
        # 开启新架构
        content = content.replace(
            "ENABLE_QUERY_EXPANSION=false",
            "ENABLE_QUERY_EXPANSION=true"
        )
        content = content.replace(
            "ENABLE_MULTI_QUERY_RETRIEVAL=false",
            "ENABLE_MULTI_QUERY_RETRIEVAL=true"
        )
        content = content.replace(
            "ENABLE_HIERARCHICAL_SUMMARIZE=false",
            "ENABLE_HIERARCHICAL_SUMMARIZE=true"
        )
        content = content.replace(
            "ENABLE_RERANK=true",
            "ENABLE_RERANK=false"
        )
    else:
        # 回退到旧架构
        content = content.replace(
            "ENABLE_QUERY_EXPANSION=true",
            "ENABLE_QUERY_EXPANSION=false"
        )
        content = content.replace(
            "ENABLE_MULTI_QUERY_RETRIEVAL=true",
            "ENABLE_MULTI_QUERY_RETRIEVAL=false"
        )
        content = content.replace(
            "ENABLE_HIERARCHICAL_SUMMARIZE=true",
            "ENABLE_HIERARCHICAL_SUMMARIZE=false"
        )
        content = content.replace(
            "ENABLE_RERANK=false",
            "ENABLE_RERANK=true"
        )

    env_file.write_text(content, encoding='utf-8')
    print(f"✅ .env配置已切换到 {'新架构' if enable_new_arch else '旧架构'}")

def analyze_test_result(output_dir: Path):
    """分析测试结果"""
    result = {
        "retrieved_ids": [],
        "cited_ids": [],
        "recall_rate": 0.0,
        "citation_count": 0,
        "api_cost": 0.0,
        "expanded_queries": []
    }

    # 1. 检查retrieval_analysis.md
    retrieval_file = output_dir / "analysis" / "retrieval_analysis.md"
    if retrieval_file.exists():
        content = retrieval_file.read_text(encoding='utf-8')
        for text_id in MISSING_TEXT_IDS:
            if text_id in content:
                result["retrieved_ids"].append(text_id)

    result["recall_rate"] = len(result["retrieved_ids"]) / len(MISSING_TEXT_IDS) * 100

    # 2. 检查citation_mapping.md
    citation_file = output_dir / "analysis" / "citation_mapping.md"
    if citation_file.exists():
        content = citation_file.read_text(encoding='utf-8')
        for text_id in MISSING_TEXT_IDS:
            if text_id in content:
                result["cited_ids"].append(text_id)

    result["citation_count"] = len(result["cited_ids"])

    # 3. 检查query_expansion.json（如果有）
    query_expansion_file = output_dir / "analysis" / "query_expansion.json"
    if query_expansion_file.exists():
        try:
            data = json.loads(query_expansion_file.read_text(encoding='utf-8'))
            result["expanded_queries"] = data.get("expanded_queries", [])
        except:
            pass

    # 4. 估算API成本（粗略估算）
    # 假设：Query扩展 5次LLM调用，每次$0.01
    #       多路召回 5次Embedding调用，每次$0.005
    #       分层总结 6次LLM调用（5个维度+1个合并），每次$0.02
    if result["expanded_queries"]:
        result["api_cost"] = 0.01 * 5 + 0.005 * 5 + 0.02 * 6  # $0.195
    else:
        result["api_cost"] = 0.01 * 2 + 0.005 * 1 + 0.02 * 1  # $0.045（旧架构）

    return result

def print_comparison(old_result, new_result):
    """打印对比结果"""
    print("\n" + "="*80)
    print("📊 新旧架构对比分析（Q1）")
    print("="*80)

    print(f"\n{'指标':<25} {'旧架构':<20} {'新架构':<20} {'差异':<20}")
    print("-" * 85)

    # 召回率
    recall_diff = new_result["recall_rate"] - old_result["recall_rate"]
    print(f"{'召回率 (15个遗漏文档)':<25} "
          f"{old_result['recall_rate']:<20.1f}% "
          f"{new_result['recall_rate']:<20.1f}% "
          f"{recall_diff:+.1f}%")

    # 最终引用数
    citation_diff = new_result["citation_count"] - old_result["citation_count"]
    print(f"{'最终引用数':<25} "
          f"{old_result['citation_count']}/15{'':<14} "
          f"{new_result['citation_count']}/15{'':<14} "
          f"{citation_diff:+d}")

    # API成本
    cost_diff = new_result["api_cost"] - old_result["api_cost"]
    cost_increase_pct = (new_result["api_cost"] / old_result["api_cost"] - 1) * 100
    print(f"{'API成本 (单次Q1测试)':<25} "
          f"${old_result['api_cost']:<19.3f} "
          f"${new_result['api_cost']:<19.3f} "
          f"+${cost_diff:.3f} ({cost_increase_pct:+.0f}%)")

    print("\n" + "="*80)
    print("💡 关键发现")
    print("="*80)

    # 召回改善
    if recall_diff > 20:
        print(f"  ✅ 召回率显著提升：{recall_diff:+.1f}%")
    elif recall_diff > 0:
        print(f"  ✓  召回率小幅提升：{recall_diff:+.1f}%")
    else:
        print(f"  ⚠️ 召回率未改善")

    # 引用改善
    if citation_diff >= 10:
        print(f"  ✅ 引用数大幅增加：{citation_diff:+d}个文档")
    elif citation_diff > 0:
        print(f"  ✓  引用数小幅增加：{citation_diff:+d}个文档")
    else:
        print(f"  ⚠️ 引用数未改善")

    # 成本分析
    if cost_increase_pct < 200:
        print(f"  ✅ 成本增加可控：+{cost_increase_pct:.0f}%")
    else:
        print(f"  ⚠️ 成本增加较高：+{cost_increase_pct:.0f}%")

    # Query扩展示例
    if new_result["expanded_queries"]:
        print(f"\n{'='*80}")
        print("🔍 Query扩展示例")
        print("="*80)
        print("  原始问题: 请总结2015年CDU/CSU在难民政策上的立场")
        print("  扩展查询:")
        for i, query in enumerate(new_result["expanded_queries"], 1):
            print(f"    {i}. {query}")

    # 遗漏文档召回详情
    print(f"\n{'='*80}")
    print("📋 遗漏文档召回详情（15个文档）")
    print("="*80)

    for text_id in MISSING_TEXT_IDS:
        old_recalled = text_id in old_result["retrieved_ids"]
        new_recalled = text_id in new_result["retrieved_ids"]

        if new_recalled and not old_recalled:
            print(f"  ✅ {text_id}: 新架构召回成功！")
        elif new_recalled and old_recalled:
            print(f"  ✓  {text_id}: 两者都召回")
        elif not new_recalled and not old_recalled:
            print(f"  ❌ {text_id}: 仍未召回")
        else:
            print(f"  ⚠️ {text_id}: 旧架构召回但新架构未召回（异常）")

def main():
    """主演示流程"""
    print("="*80)
    print("🎬 新旧架构对比演示")
    print("="*80)
    print("\n本演示将对比Q1在新旧架构下的效果差异")
    print("注意：本演示需要运行两次完整测试，耗时约40-60分钟\n")

    input("按Enter开始演示...")

    # 演示流程说明
    print("\n演示流程：")
    print("  1. 切换到旧架构 → 运行Q1测试 → 分析结果")
    print("  2. 切换到新架构 → 运行Q1测试 → 分析结果")
    print("  3. 对比两次测试结果")
    print("  4. 生成对比报告")

    print("\n" + "="*80)
    print("⚠️ 重要提示")
    print("="*80)
    print("  - 本演示会修改.env配置文件")
    print("  - 需要确保Pinecone连接正常")
    print("  - 需要确保Gemini API额度充足")
    print("  - 建议在测试环境运行")

    confirm = input("\n确认继续？(y/n): ")
    if confirm.lower() != 'y':
        print("❌ 演示已取消")
        return

    # Phase 1: 旧架构测试
    print("\n" + "="*80)
    print("📊 Phase 1: 旧架构测试")
    print("="*80)

    modify_env_config(enable_new_arch=False)
    print("  请手动运行: python test_langgraph_complete.py --test-single Q1")
    print("  等待测试完成后，按Enter继续...")
    input()

    # 查找最新的Q1输出目录
    q1_dirs_old = sorted(Path("outputs").glob("Q1_*"), reverse=True)
    if not q1_dirs_old:
        print("❌ 未找到旧架构测试结果")
        return

    old_result = analyze_test_result(q1_dirs_old[0])
    print(f"  ✅ 旧架构测试完成")
    print(f"     召回率: {old_result['recall_rate']:.1f}%")
    print(f"     引用数: {old_result['citation_count']}/15")

    # Phase 2: 新架构测试
    print("\n" + "="*80)
    print("📊 Phase 2: 新架构测试")
    print("="*80)

    modify_env_config(enable_new_arch=True)
    print("  请手动运行: python test_langgraph_complete.py --test-single Q1")
    print("  等待测试完成后，按Enter继续...")
    input()

    q1_dirs_new = sorted(Path("outputs").glob("Q1_*"), reverse=True)
    if not q1_dirs_new:
        print("❌ 未找到新架构测试结果")
        return

    new_result = analyze_test_result(q1_dirs_new[0])
    print(f"  ✅ 新架构测试完成")
    print(f"     召回率: {new_result['recall_rate']:.1f}%")
    print(f"     引用数: {new_result['citation_count']}/15")

    # Phase 3: 对比分析
    print_comparison(old_result, new_result)

    # 生成对比报告
    report_file = Path("outputs") / f"architecture_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    generate_comparison_report(old_result, new_result, report_file)
    print(f"\n📄 对比报告已生成: {report_file}")

def generate_comparison_report(old_result, new_result, output_file):
    """生成详细对比报告"""
    report = f"""# 新旧架构对比报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 测试问题
Q1: 请总结2015年CDU/CSU在难民政策上的立场

## 对比结果

### 召回率对比
- 旧架构: {old_result['recall_rate']:.1f}% ({len(old_result['retrieved_ids'])}/15)
- 新架构: {new_result['recall_rate']:.1f}% ({len(new_result['retrieved_ids'])}/15)
- 提升: {new_result['recall_rate'] - old_result['recall_rate']:+.1f}%

### 最终引用数对比
- 旧架构: {old_result['citation_count']}/15
- 新架构: {new_result['citation_count']}/15
- 提升: {new_result['citation_count'] - old_result['citation_count']:+d}

### API成本对比
- 旧架构: ${old_result['api_cost']:.3f}
- 新架构: ${new_result['api_cost']:.3f}
- 增加: +${new_result['api_cost'] - old_result['api_cost']:.3f} ({(new_result['api_cost']/old_result['api_cost']-1)*100:+.0f}%)

## Query扩展示例

原始问题: 请总结2015年CDU/CSU在难民政策上的立场

扩展查询:
"""

    for i, query in enumerate(new_result["expanded_queries"], 1):
        report += f"{i}. {query}\n"

    report += f"""
## 遗漏文档召回详情

| Text ID | 旧架构 | 新架构 | 状态 |
|---------|--------|--------|------|
"""

    for text_id in MISSING_TEXT_IDS:
        old_recalled = text_id in old_result["retrieved_ids"]
        new_recalled = text_id in new_result["retrieved_ids"]

        old_mark = "✅" if old_recalled else "❌"
        new_mark = "✅" if new_recalled else "❌"

        if new_recalled and not old_recalled:
            status = "✅ 新架构召回"
        elif new_recalled and old_recalled:
            status = "✓ 都召回"
        else:
            status = "❌ 未召回"

        report += f"| {text_id} | {old_mark} | {new_mark} | {status} |\n"

    report += f"""
## 结论

1. **召回率改善**: {new_result['recall_rate'] - old_result['recall_rate']:+.1f}%
2. **引用数改善**: {new_result['citation_count'] - old_result['citation_count']:+d}个文档
3. **成本增加**: {(new_result['api_cost']/old_result['api_cost']-1)*100:+.0f}%

{'✅ 新架构显著改善了检索和引用质量' if new_result['citation_count'] > old_result['citation_count'] else '⚠️ 新架构未达到预期效果'}
"""

    output_file.write_text(report, encoding='utf-8')

if __name__ == "__main__":
    main()
