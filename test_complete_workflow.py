#!/usr/bin/env python3
"""
完整LangGraph Workflow测试（包含ReRank）
对比与简化脚本的答案质量差异
"""

import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger
from src.graph.workflow import QuestionAnswerWorkflow

logger = setup_logger()


def test_complete_workflow():
    """测试完整的LangGraph workflow"""

    logger.info("="*80)
    logger.info("🧪 开始完整Workflow测试（包含ReRank）")
    logger.info("="*80)

    # 初始化workflow
    logger.info("🔧 初始化QuestionAnswerWorkflow...")
    workflow = QuestionAnswerWorkflow()
    logger.info("✅ Workflow初始化完成")

    # 测试问题（与简化脚本相同）
    test_questions = [
        {
            "id": "Q1",
            "type": "总结类",
            "question": "请总结2015年德国议会关于难民政策的主要讨论内容"
        },
        {
            "id": "Q2",
            "type": "对比类",
            "question": "CDU/CSU和SPD在2015年对难民政策的立场有什么不同？"
        },
        {
            "id": "Q3",
            "type": "观点类",
            "question": "2015年德国议会议员对欧盟一体化的主要观点是什么？"
        },
        {
            "id": "Q4",
            "type": "事实查询",
            "question": "2015年德国议会有哪些重要法案被讨论？"
        }
    ]

    results = []

    for test_case in test_questions:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 测试问题 {test_case['id']}: {test_case['type']}")
        logger.info(f"   问题: {test_case['question']}")
        logger.info(f"{'='*80}\n")

        start_time = time.time()

        try:
            # 调用完整workflow
            result = workflow.run(test_case['question'])

            total_time = time.time() - start_time

            # 提取答案和中间状态
            answer = result.get("final_answer", "")
            intent_result = result.get("intent_result", {})
            classify_result = result.get("classify_result", {})
            extract_result = result.get("extract_result", {})
            decompose_result = result.get("decompose_result", {})
            retrieval_results = result.get("retrieval_results", [])
            rerank_results = result.get("rerank_results", [])

            # 统计检索和rerank信息
            total_chunks_before_rerank = sum(len(r.get("chunks", [])) for r in retrieval_results)
            total_chunks_after_rerank = sum(len(r.get("reranked_chunks", [])) for r in rerank_results)

            logger.info(f"✅ {test_case['id']} 完成")
            logger.info(f"   总耗时: {total_time:.2f} 秒")
            logger.info(f"   意图分析: {intent_result.get('intent_type', 'N/A')}")
            logger.info(f"   问题类型: {classify_result.get('question_type', 'N/A')}")
            logger.info(f"   检索前块数: {total_chunks_before_rerank}")
            logger.info(f"   ReRank后块数: {total_chunks_after_rerank}")
            logger.info(f"   答案长度: {len(answer)} 字符")

            # 显示前200字符答案预览
            preview = answer[:200] + "..." if len(answer) > 200 else answer
            logger.info(f"\n📝 答案预览:\n{preview}\n")

            # 收集结果
            test_result = {
                "question_id": test_case['id'],
                "question_type": test_case['type'],
                "question": test_case['question'],
                "total_time": round(total_time, 2),
                "intent_type": intent_result.get('intent_type', 'N/A'),
                "classify_type": classify_result.get('question_type', 'N/A'),
                "extract_params": extract_result,
                "sub_questions": decompose_result.get('sub_questions', []),
                "chunks_before_rerank": total_chunks_before_rerank,
                "chunks_after_rerank": total_chunks_after_rerank,
                "answer": answer,
                "full_state": result
            }

            results.append(test_result)

        except Exception as e:
            logger.error(f"❌ {test_case['id']} 失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            results.append({
                "question_id": test_case['id'],
                "question_type": test_case['type'],
                "question": test_case['question'],
                "status": "failed",
                "error": str(e)
            })

    # 保存结果
    logger.info(f"\n{'='*80}")
    logger.info("💾 保存测试结果...")
    logger.info(f"{'='*80}\n")

    # 保存详细JSON
    output_file = project_root / "complete_workflow_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ 详细结果已保存: {output_file}")

    # 生成对比报告
    generate_comparison_report(results)

    return results


def generate_comparison_report(results):
    """生成与简化脚本的对比报告"""

    logger.info("📊 生成对比报告...")

    report_file = project_root / "WORKFLOW_COMPARISON_REPORT.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 完整Workflow vs 简化脚本对比报告\n\n")
        f.write("## 测试配置\n\n")
        f.write("- **测试时间**: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        f.write("- **数据范围**: 2015年德国议会数据\n")
        f.write("- **Workflow**: LangGraph CoA (Chain of Agents)\n")
        f.write("- **ReRank**: Cohere rerank-v3.5\n")
        f.write("- **Embedding**: BGE-M3 (local, 1024-dim)\n")
        f.write("- **Vector DB**: Pinecone (german-bge index)\n\n")

        f.write("## 测试结果对比\n\n")

        for result in results:
            if result.get('status') == 'failed':
                f.write(f"### {result['question_id']}: {result['question_type']}\n\n")
                f.write(f"**问题**: {result['question']}\n\n")
                f.write(f"**状态**: ❌ 失败\n\n")
                f.write(f"**错误**: {result['error']}\n\n")
                f.write("---\n\n")
                continue

            f.write(f"### {result['question_id']}: {result['question_type']}\n\n")
            f.write(f"**问题**: {result['question']}\n\n")

            f.write(f"#### Workflow处理流程\n\n")
            f.write(f"- **意图类型**: {result['intent_type']}\n")
            f.write(f"- **问题分类**: {result['classify_type']}\n")
            f.write(f"- **提取参数**: {json.dumps(result['extract_params'], ensure_ascii=False)}\n")
            f.write(f"- **子问题数**: {len(result.get('sub_questions', []))}\n")
            f.write(f"- **ReRank前**: {result['chunks_before_rerank']} 个文档块\n")
            f.write(f"- **ReRank后**: {result['chunks_after_rerank']} 个文档块\n")
            f.write(f"- **总耗时**: {result['total_time']} 秒\n\n")

            f.write(f"#### 完整Workflow答案\n\n")
            f.write(f"```\n{result['answer']}\n```\n\n")

            f.write("#### 答案质量分析\n\n")
            f.write("待人工评估：\n")
            f.write("- [ ] 答案完整性\n")
            f.write("- [ ] 信息准确性\n")
            f.write("- [ ] 引用质量\n")
            f.write("- [ ] 逻辑连贯性\n")
            f.write("- [ ] 与简化脚本对比\n\n")

            f.write("---\n\n")

        f.write("## 总体对比\n\n")
        f.write("### 完整Workflow优势\n\n")
        f.write("1. **多阶段处理**: 意图分析 → 分类 → 参数提取 → 分解 → 检索 → ReRank → 总结\n")
        f.write("2. **ReRank优化**: Cohere API重新排序文档，提升相关性\n")
        f.write("3. **子问题分解**: 复杂问题拆分为多个子问题，检索更精准\n")
        f.write("4. **参数提取**: 自动提取年份、党派、发言人等过滤条件\n\n")

        f.write("### 简化脚本特点\n\n")
        f.write("1. **直接检索**: 问题 → Embedding → Pinecone查询 → LLM生成\n")
        f.write("2. **无ReRank**: 直接使用向量相似度排序\n")
        f.write("3. **固定top_k**: 检索固定数量文档（10个）\n")
        f.write("4. **简单快速**: 适合简单问题，耗时更短\n\n")

        f.write("### 性能对比\n\n")
        f.write("| 指标 | 完整Workflow | 简化脚本 |\n")
        f.write("|------|-------------|--------|\n")

        avg_time = sum(r['total_time'] for r in results if 'total_time' in r) / len([r for r in results if 'total_time' in r])
        f.write(f"| 平均耗时 | {avg_time:.2f}秒 | 28-32秒 |\n")

        avg_chunks_before = sum(r['chunks_before_rerank'] for r in results if 'chunks_before_rerank' in r) / len([r for r in results if 'chunks_before_rerank' in r])
        avg_chunks_after = sum(r['chunks_after_rerank'] for r in results if 'chunks_after_rerank' in r) / len([r for r in results if 'chunks_after_rerank' in r])
        f.write(f"| 文档块数 | ReRank前: {avg_chunks_before:.1f}, ReRank后: {avg_chunks_after:.1f} | 10个 |\n")

        f.write("| 处理阶段 | 7个节点 | 2步（检索+生成） |\n")
        f.write("| 适用场景 | 复杂问题 | 简单问题 |\n\n")

        f.write("## 检索完整性分析\n\n")
        f.write("### Q1问题：\"请总结2015年德国议会关于难民政策的主要讨论内容\"\n\n")
        f.write("**简化脚本答案提到**: \"检索到的内容仅包含2015年5月和10月两个时间点的三位发言人的观点\"\n\n")
        f.write("**需要验证**:\n")
        f.write("1. 2015年其他月份是否讨论了难民政策？\n")
        f.write("2. top_k=10是否限制了检索范围？\n")
        f.write("3. 完整workflow的ReRank是否检索到更多时间点？\n\n")

        # 分析Q1的检索结果
        q1_result = next((r for r in results if r['question_id'] == 'Q1'), None)
        if q1_result and 'full_state' in q1_result:
            retrieval_results = q1_result['full_state'].get('retrieval_results', [])
            if retrieval_results:
                f.write("**完整Workflow检索到的时间点**:\n\n")
                dates = set()
                for retrieval in retrieval_results:
                    for chunk in retrieval.get('chunks', []):
                        metadata = chunk.get('metadata', {})
                        date = metadata.get('date', 'N/A')
                        if date != 'N/A':
                            dates.add(date)

                dates_sorted = sorted(list(dates))
                f.write(f"- 共 {len(dates_sorted)} 个不同日期\n")
                for date in dates_sorted[:20]:  # 显示前20个
                    f.write(f"- {date}\n")

                if len(dates_sorted) > 20:
                    f.write(f"- ... 还有 {len(dates_sorted) - 20} 个日期\n")
                f.write("\n")

        f.write("## 结论\n\n")
        f.write("**待完成**:\n")
        f.write("1. 人工评估答案质量差异\n")
        f.write("2. 确认检索完整性问题\n")
        f.write("3. 决定生产环境使用哪种方案\n\n")

    logger.info(f"✅ 对比报告已生成: {report_file}")


if __name__ == "__main__":
    try:
        results = test_complete_workflow()

        success_count = len([r for r in results if r.get('status') != 'failed'])
        failed_count = len([r for r in results if r.get('status') == 'failed'])

        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 测试完成!")
        logger.info(f"   成功: {success_count}")
        logger.info(f"   失败: {failed_count}")
        logger.info(f"{'='*80}\n")

        exit(0 if failed_count == 0 else 1)

    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
