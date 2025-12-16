#!/usr/bin/env python3
"""
基于LangGraph完整工作流的多年份RAG测试
优化版本 - 解决参数提取、检索策略、可观测性问题

支持德语和中文两种模式：
  python test_langgraph_complete.py              # 默认德语
  python test_langgraph_complete.py --language chinese  # 中文模式
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger

logger = setup_logger()

# 7个测试问题（德语版）
TEST_QUESTIONS_DE = [
    {
        "id": 1,
        "question": "Bitte fassen Sie die wichtigsten Veränderungen in der Flüchtlingspolitik der CDU/CSU seit 2015 zusammen.",
        "type": "多年变化分析",
        "years": "2015-2024",
        "expected_years": list(range(2015, 2025))
    },
    {
        "id": 2,
        "question": "Welche Positionen vertraten die verschiedenen Parteien im Deutschen Bundestag 2017 zur Reform des Fachkräfteeinwanderungsgesetzes?",
        "type": "单年多党派对比",
        "years": "2017",
        "expected_years": [2017]
    },
    {
        "id": 3,
        "question": "Was waren die Hauptpositionen und Forderungen der Grünen zur Migrationsfrage im Deutschen Bundestag 2015?",
        "type": "单年单党派观点",
        "years": "2015",
        "expected_years": [2015]
    },
    {
        "id": 4,
        "question": "Wie haben sich die Diskussionen der verschiedenen Parteien im Deutschen Bundestag über die Familienzusammenführung von Flüchtlingen zwischen 2015 und 2018 entwickelt?",
        "type": "跨年多党派变化",
        "years": "2015-2018",
        "expected_years": list(range(2015, 2019))
    },
    {
        "id": 5,
        "question": "Bitte vergleichen Sie die Positionen der Unionsparteien und der Grünen zur Integrationspolitik zwischen 2015 und 2017.",
        "type": "跨年两党对比",
        "years": "2015-2017",
        "expected_years": list(range(2015, 2018))
    },
    {
        "id": 6,
        "question": "Wie haben sich die Positionen der CDU/CSU zur Migrationspolitik zwischen 2017 und 2019 im Vergleich verändert?",
        "type": "离散年份对比",
        "years": "2017, 2019",
        "expected_years": [2017, 2019]
    },
    {
        "id": 7,
        "question": "Welche wichtigen Ansichten und Vorschläge vertrat die AfD zur Flüchtlingspolitik im Jahr 2018?",
        "type": "单年单党派观点",
        "years": "2018",
        "expected_years": [2018]
    }
]

# 7个测试问题（中文版）
TEST_QUESTIONS_ZH = [
    {
        "id": 1,
        "question": "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化。",
        "type": "多年变化分析",
        "years": "2015-2024",
        "expected_years": list(range(2015, 2025))
    },
    {
        "id": 2,
        "question": "2017年，德国联邦议会中各党派对专业人才移民制度改革分别持什么立场？",
        "type": "单年多党派对比",
        "years": "2017",
        "expected_years": [2017]
    },
    {
        "id": 3,
        "question": "2015年，德国联邦议会中绿党在移民国籍问题上的主要立场和诉求是什么？",
        "type": "单年单党派观点",
        "years": "2015",
        "expected_years": [2015]
    },
    {
        "id": 4,
        "question": "在2015年到2018年期间，德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化？",
        "type": "跨年多党派变化",
        "years": "2015-2018",
        "expected_years": list(range(2015, 2019))
    },
    {
        "id": 5,
        "question": "请对比2015-2017年联盟党与绿党在移民融合政策方面的主张。",
        "type": "跨年两党对比",
        "years": "2015-2017",
        "expected_years": list(range(2015, 2018))
    },
    {
        "id": 6,
        "question": "2019年与2017年相比，联邦议会关于难民遣返的讨论有何变化？",
        "type": "两年对比",
        "years": "2017, 2019",
        "expected_years": [2017, 2019]
    },
    {
        "id": 7,
        "question": "新冠疫情期间（主要是2020年），联邦议院对坚持气候目标的看法发生了什么变化？请使用2019-2021年的资料进行回答。必要时给出具体引语。",
        "type": "跨年疫情影响分析",
        "years": "2019-2021",
        "expected_years": list(range(2019, 2022))
    }
]


def create_pinecone_workflow():
    """
    创建使用Pinecone的LangGraph工作流

    使用增强版节点:
    - EnhancedExtractNode: 支持时间语义理解
    - PineconeRetrieveNode: 支持多年份分层检索
    """
    from langgraph.graph import StateGraph, END
    from src.graph.state import GraphState
    from src.graph.nodes import ClassifyNode, ReRankNode
    from src.graph.nodes.intent_enhanced import EnhancedIntentNode
    from src.graph.nodes.extract_enhanced import EnhancedExtractNode
    from src.graph.nodes.decompose_enhanced import EnhancedDecomposeNode
    from src.graph.nodes.summarize_enhanced import EnhancedSummarizeNode
    from src.graph.nodes.exception_enhanced import EnhancedExceptionNode
    from src.graph.nodes.retrieve_pinecone import PineconeRetrieveNode
    from src.graph.nodes.query_expansion import QueryExpansionNode

    logger.info("[Workflow] 创建Pinecone优化版工作流...")

    # 【重要】启用生产模式以触发两阶段重试机制
    from src.config import settings
    settings.production_mode = True
    logger.info("[Workflow] 🔥 已启用生产模式（含两阶段重试机制）")

    # 创建节点
    intent_node = EnhancedIntentNode()
    classify_node = ClassifyNode()
    extract_node = EnhancedExtractNode()  # 增强版
    decompose_node = EnhancedDecomposeNode()
    query_expansion_node = QueryExpansionNode(expansion_count=5)  # Query扩展节点
    retrieve_node = PineconeRetrieveNode(
        top_k=50,  # 提升到50
        enable_multi_year_strategy=True,
        limit_per_year=5,
        enable_concurrent=True  # 启用并发检索，大幅提速
    )
    rerank_node = ReRankNode()
    summarize_node = EnhancedSummarizeNode()
    exception_node = EnhancedExceptionNode()

    logger.info("[Workflow] 节点创建完成")

    # 构建工作流图
    workflow = StateGraph(GraphState)

    # 添加节点
    workflow.add_node("intent_analysis", intent_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("query_expansion", query_expansion_node)  # Query扩展节点
    workflow.add_node("retrieve", retrieve_node)
    # workflow.add_node("rerank", rerank_node)  # 【Phase 4】禁用ReRank：Cohere过滤了BGE-M3的最佳结果
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("exception", exception_node)

    # 设置入口点
    workflow.set_entry_point("intent_analysis")

    # 路由函数
    def route_after_intent(state):
        if state.get("error"):
            return "exception"
        intent = state.get("intent")
        if intent == "complex":
            return "classify"
        else:
            return "extract"

    def route_after_classify(state):
        if state.get("error"):
            return "exception"
        return "extract"

    def route_after_extract(state):
        if state.get("error"):
            return "exception"
        is_decomposed = state.get("is_decomposed", False)
        if is_decomposed:
            return "decompose"
        else:
            return "retrieve"

    def route_after_decompose(state):
        if state.get("error"):
            return "exception"
        return "query_expansion"  # 先进行Query扩展，再检索

    def route_after_retrieve(state):
        """【Phase 4修改】直接返回summarize，跳过ReRank"""
        if state.get("error"):
            return "exception"
        no_material_found = state.get("no_material_found", False)
        if no_material_found:
            return "exception"
        else:
            return "summarize"  # 直接到Summarize，跳过ReRank

    def route_after_rerank(state):
        if state.get("error"):
            return "exception"
        reranked_results = state.get("reranked_results", [])
        if not reranked_results:
            return "exception"
        else:
            return "summarize"

    # 添加路由
    workflow.add_conditional_edges(
        "intent_analysis",
        route_after_intent,
        {"classify": "classify", "extract": "extract", "exception": "exception"}
    )
    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {"extract": "extract", "exception": "exception"}
    )
    workflow.add_conditional_edges(
        "extract",
        route_after_extract,
        {"decompose": "decompose", "retrieve": "retrieve", "exception": "exception"}
    )
    workflow.add_conditional_edges(
        "decompose",
        route_after_decompose,
        {"query_expansion": "query_expansion", "exception": "exception"}
    )
    # Query扩展后直接进入检索
    workflow.add_edge("query_expansion", "retrieve")
    # 【Phase 4修改】Retrieve -> Summarize (跳过ReRank)
    # 原因：Cohere ReRank过滤掉了BGE-M3检索排名第1的目标文档
    workflow.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"summarize": "summarize", "exception": "exception"}
    )
    # workflow.add_conditional_edges(
    #     "rerank",
    #     route_after_rerank,
    #     {"summarize": "summarize", "exception": "exception"}
    # )  # 【Phase 4】禁用ReRank节点后，从rerank出发的edges也要移除

    # 添加结束边
    workflow.add_edge("summarize", END)
    workflow.add_edge("exception", END)

    logger.info("[Workflow] 工作流图构建完成")

    return workflow.compile()


def test_one_question(workflow, question_data: dict, total_questions: int = 7):
    """测试一个问题"""
    from src.graph.state import create_initial_state

    qid = question_data['id']
    question = question_data['question']
    qtype = question_data['type']
    years = question_data['years']
    expected_years = question_data['expected_years']

    logger.info(f"\n{'='*100}")
    logger.info(f"📝 问题 {qid}/{total_questions}: {qtype} ({years})")
    logger.info(f"{'='*100}")
    logger.info(f"问题: {question}")
    logger.info(f"期望年份: {expected_years}")

    # 创建初始状态
    initial_state = create_initial_state(question)

    # 运行工作流
    start_time = time.time()
    try:
        final_state = workflow.invoke(initial_state)
        total_time = time.time() - start_time

        logger.info(f"\n{'='*100}")
        logger.info(f"✅ 问题 {qid} 完成，总耗时: {total_time:.2f}秒")
        logger.info(f"{'='*100}")

        # 收集结果
        result = {
            "question_id": qid,
            "question": question,
            "type": qtype,
            "years": years,
            "expected_years": expected_years,
            "total_time": total_time,

            # 内部思考过程
            "intent": final_state.get("intent"),
            "question_type": final_state.get("question_type"),
            "parameters": final_state.get("parameters", {}),
            "extraction_thinking": final_state.get("extraction_thinking", ""),
            "retrieval_thinking": final_state.get("retrieval_thinking", ""),

            # 检索信息
            "retrieval_results": final_state.get("retrieval_results", []),
            "overall_year_distribution": final_state.get("overall_year_distribution", {}),
            "reranked_results": final_state.get("reranked_results", []),

            # 最终答案
            "final_answer": final_state.get("final_answer", ""),
            "error": final_state.get("error"),

            # 子问题信息（如果有）
            "sub_questions": final_state.get("sub_questions"),
            "sub_answers": final_state.get("sub_answers"),
        }

        # 验证年份覆盖
        actual_years = list(final_state.get("overall_year_distribution", {}).keys())
        missing_years = [y for y in expected_years if str(y) not in actual_years]
        if missing_years:
            logger.warning(f"⚠️ 缺失年份: {missing_years}")
            result["missing_years"] = missing_years

        # 打印关键信息
        logger.info(f"\n=== 问题 {qid} 结果摘要 ===")
        logger.info(f"意图: {result['intent']}")
        logger.info(f"类型: {result['question_type']}")
        logger.info(f"提取参数: {json.dumps(result['parameters'], ensure_ascii=False)}")
        logger.info(f"年份分布: {result['overall_year_distribution']}")
        logger.info(f"答案长度: {len(result['final_answer'])} 字符")

        if result.get("sub_questions"):
            logger.info(f"子问题数: {len(result['sub_questions'])}")

        # 打印完整答案
        logger.info(f"\n{'='*100}")
        logger.info(f"📄 问题 {qid} 完整答案:")
        logger.info(f"{'='*100}")
        logger.info(result['final_answer'])
        logger.info(f"{'='*100}\n")

        # 🆕 生成完整引用报告
        try:
            from generate_full_ref_report import FullRefReportGenerator
            generator = FullRefReportGenerator(output_dir="outputs")
            report_dir = generator.generate_report(final_state, question_id=f"Q{qid}")
            logger.info(f"[FullRef] ✅ 完整引用报告已生成: {report_dir}")
            result['report_dir'] = str(report_dir)
        except Exception as e:
            logger.warning(f"[FullRef] ⚠️ 报告生成失败: {str(e)}")

        return result

    except Exception as e:
        logger.error(f"❌ 问题 {qid} 测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            "question_id": qid,
            "question": question,
            "type": qtype,
            "error": str(e),
            "total_time": time.time() - start_time
        }


def generate_markdown_report(results: list, output_file: Path):
    """生成格式化的Markdown报告"""
    report_lines = []

    report_lines.append("# 多年份RAG系统完整测试报告")
    report_lines.append(f"\n**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"\n**测试问题数**: {len(results)}")
    report_lines.append(f"\n---\n")

    # 总览表格
    report_lines.append("## 测试总览\n")
    report_lines.append("| ID | 类型 | 期望年份 | 实际年份 | 耗时(秒) | 状态 |")
    report_lines.append("|----|------|----------|----------|----------|------|")

    for r in results:
        qid = r['question_id']
        qtype = r['type']
        expected = r.get('expected_years', [])
        actual = list(r.get('overall_year_distribution', {}).keys())
        duration = r.get('total_time', 0)
        status = "❌错误" if r.get('error') else "✅成功"

        report_lines.append(
            f"| Q{qid} | {qtype} | {len(expected)}年 | {len(actual)}年 | {duration:.2f} | {status} |"
        )

    report_lines.append("\n---\n")

    # 每个问题的详细结果
    for r in results:
        qid = r['question_id']
        question = r['question']
        qtype = r['type']

        report_lines.append(f"## 问题 {qid}: {qtype}\n")
        report_lines.append(f"**问题**: {question}\n")

        if r.get('error'):
            report_lines.append(f"**错误**: {r['error']}\n")
            report_lines.append("---\n")
            continue

        # 参数提取
        report_lines.append("### 参数提取\n")
        report_lines.append("```json")
        report_lines.append(json.dumps(r.get('parameters', {}), ensure_ascii=False, indent=2))
        report_lines.append("```\n")

        # 检索信息
        report_lines.append("### 检索信息\n")
        report_lines.append(f"- **意图**: {r.get('intent')}")
        report_lines.append(f"- **问题类型**: {r.get('question_type')}")
        report_lines.append(f"- **年份分布**: {r.get('overall_year_distribution', {})}")
        report_lines.append(f"- **检索文档数**: {sum(len(rr.get('chunks', [])) for rr in r.get('retrieval_results', []))}")
        report_lines.append(f"- **ReRank后文档数**: {len(r.get('reranked_results', []))}\n")

        # 内部思考过程
        if r.get('extraction_thinking'):
            report_lines.append("### 参数提取思考过程\n")
            report_lines.append("```")
            report_lines.append(r['extraction_thinking'])
            report_lines.append("```\n")

        if r.get('retrieval_thinking'):
            report_lines.append("### 检索思考过程\n")
            report_lines.append("```")
            report_lines.append(r['retrieval_thinking'])
            report_lines.append("```\n")

        # 子问题（如果有）
        if r.get('sub_questions'):
            report_lines.append("### 子问题拆解\n")
            for i, sq in enumerate(r['sub_questions'], 1):
                report_lines.append(f"{i}. {sq}")
            report_lines.append("")

        # 最终答案
        report_lines.append("### 最终答案\n")
        report_lines.append(r.get('final_answer', '无答案'))
        report_lines.append("\n---\n")

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    logger.info(f"✅ Markdown报告已生成: {output_file}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='德国议会RAG系统测试 - 支持德语和中文',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test_langgraph_complete.py                    # 德语模式（默认）
  python test_langgraph_complete.py --language chinese # 中文模式
  python test_langgraph_complete.py --language german  # 德语模式（显式）
        """
    )
    parser.add_argument(
        '--language',
        choices=['german', 'chinese', 'de', 'zh'],
        default='german',
        help='选择语言模式：german/de (德语，默认) 或 chinese/zh (中文)'
    )
    args = parser.parse_args()

    # 确定使用的问题集
    if args.language in ['chinese', 'zh']:
        TEST_QUESTIONS = TEST_QUESTIONS_ZH
        language_name = "中文"
        logger.info("🌏 语言模式: 中文")
    else:
        TEST_QUESTIONS = TEST_QUESTIONS_DE
        language_name = "Deutsch (德语)"
        logger.info("🇩🇪 语言模式: Deutsch (德语)")

    logger.info("="*100)
    logger.info(f"🚀 多年份RAG系统完整测试 (LangGraph优化版) - {language_name}")
    logger.info("="*100)

    logger.info("\n优化项:")
    logger.info("  1. ✅ 使用LangGraph完整工作流")
    logger.info("  2. ✅ 单年针对性检索 (target_year优化)")
    logger.info("  3. ✅ 去重机制 (避免重复文档)")
    logger.info("  4. ✅ 并行检索 (多子问题并行)")
    logger.info("  5. ✅ 详细内部思考过程输出")
    logger.info("  6. ✅ 完整引用报告生成\n")

    # 1. 创建工作流
    logger.info("\n📦 1. 创建Pinecone优化版工作流")
    logger.info("-" * 100)
    workflow = create_pinecone_workflow()
    logger.info("✅ 工作流创建完成\n")

    # 2. 运行测试
    logger.info(f"\n📋 2. 运行7个测试问题 ({language_name})")
    logger.info("-" * 100)

    results = []
    for question_data in TEST_QUESTIONS:
        try:
            result = test_one_question(workflow, question_data, total_questions=len(TEST_QUESTIONS))
            results.append(result)
            time.sleep(3)  # 避免API速率限制
        except Exception as e:
            logger.error(f"❌ 问题 {question_data['id']} 测试失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    # 3. 生成报告
    logger.info("\n📊 3. 生成测试报告")
    logger.info("-" * 100)

    # JSON报告
    json_output = project_root / "langgraph_complete_test_results.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ JSON报告: {json_output}")

    # Markdown报告
    md_output = project_root / "LANGGRAPH_COMPLETE_TEST_REPORT.md"
    generate_markdown_report(results, md_output)

    # 4. 打印总结
    logger.info("\n" + "="*100)
    logger.info("📊 测试总结")
    logger.info("="*100)

    successful = [r for r in results if not r.get('error')]
    failed = [r for r in results if r.get('error')]

    logger.info(f"\n完成测试: {len(successful)}/{len(TEST_QUESTIONS)} 成功")
    logger.info(f"失败: {len(failed)}")

    if successful:
        avg_time = sum(r['total_time'] for r in successful) / len(successful)
        logger.info(f"\n平均耗时: {avg_time:.2f}秒")

        # 年份覆盖率统计
        logger.info(f"\n年份覆盖情况:")
        for r in successful:
            expected = r.get('expected_years', [])
            actual = list(r.get('overall_year_distribution', {}).keys())
            coverage = len(actual) / len(expected) * 100 if expected else 0
            logger.info(
                f"  Q{r['question_id']}: {len(actual)}/{len(expected)} 年份 "
                f"({coverage:.0f}% 覆盖率)"
            )

    logger.info(f"\n✅ 报告已保存:")
    logger.info(f"  - JSON: {json_output}")
    logger.info(f"  - Markdown: {md_output}")

    logger.info("\n" + "="*100)
    logger.info("🎉 测试完成!")
    logger.info("="*100)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
