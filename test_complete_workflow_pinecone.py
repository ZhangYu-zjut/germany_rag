#!/usr/bin/env python3
"""
完整Workflow测试（Pinecone版本）
使用完整的workflow流程（意图分析、参数提取、ReRank），但检索使用Pinecone
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
from src.llm.embeddings import GeminiEmbeddingClient
from src.llm.client import GeminiLLMClient
from pinecone import Pinecone
import requests

logger = setup_logger()


class CompletePineconeRAG:
    """完整的RAG流程（使用Pinecone）"""

    def __init__(self):
        """初始化组件"""
        # Embedding客户端
        self.embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )

        # Pinecone
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index("german-bge")

        # LLM客户端
        self.llm = GeminiLLMClient(temperature=0.0)

        # Cohere ReRank
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.rerank_model = "rerank-v3.5"

        logger.info("✅ CompletePineconeRAG初始化完成")

    def extract_parameters(self, question: str) -> dict:
        """参数提取（模拟ExtractNode）"""
        # 简单规则提取
        params = {}

        # 提取年份
        import re
        year_match = re.search(r'20\d{2}', question)
        if year_match:
            params['year'] = year_match.group()

        # 提取党派
        parties = []
        if 'CDU/CSU' in question or 'CDU' in question:
            parties.append('CDU/CSU')
        if 'SPD' in question:
            parties.append('SPD')
        if parties:
            params['parties'] = parties

        # 提取主题
        if '难民' in question or '移民' in question:
            params['topic'] = 'refugee'
        elif '欧盟' in question:
            params['topic'] = 'EU'

        logger.info(f"📝 提取参数: {json.dumps(params, ensure_ascii=False)}")
        return params

    def retrieve(self, question: str, params: dict, top_k=20) -> list:
        """检索（使用Pinecone + metadata过滤）"""
        # 生成问题向量
        query_vector = self.embedding_client.embed_text(question)

        # 构建查询参数
        query_params = {
            "vector": query_vector,
            "top_k": top_k,
            "include_metadata": True
        }

        # 添加元数据过滤
        filters = []
        if 'year' in params:
            filters.append({"year": {"$eq": params['year']}})

        if 'parties' in params and len(params['parties']) > 0:
            # Pinecone的$in过滤
            filters.append({"group": {"$in": params['parties']}})

        if filters:
            if len(filters) == 1:
                query_params["filter"] = filters[0]
            else:
                query_params["filter"] = {"$and": filters}

        # 查询Pinecone
        results = self.index.query(**query_params)

        # 提取文档块
        chunks = []
        for match in results.matches:
            chunk = {
                "id": match.id,
                "score": match.score,
                "text": match.metadata.get("text", ""),
                "metadata": match.metadata
            }
            chunks.append(chunk)

        logger.info(f"🔍 检索到 {len(chunks)} 个文档块 (top_k={top_k})")
        return chunks

    def rerank(self, question: str, chunks: list, top_n=10) -> list:
        """ReRank（使用Cohere API）"""
        if not chunks:
            return []

        # 准备文档
        documents = [chunk['text'] for chunk in chunks]

        # 调用Cohere ReRank API
        url = "https://api.cohere.com/v2/rerank"
        headers = {
            "Authorization": f"Bearer {self.cohere_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.rerank_model,
            "query": question,
            "documents": documents,
            "top_n": top_n
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            # 提取rerank结果
            reranked_chunks = []
            for item in result.get("results", []):
                index = item["index"]
                relevance_score = item["relevance_score"]

                reranked_chunk = chunks[index].copy()
                reranked_chunk["rerank_score"] = relevance_score
                reranked_chunks.append(reranked_chunk)

            logger.info(f"🎯 ReRank完成: {len(chunks)} → {len(reranked_chunks)} 个文档块")
            return reranked_chunks

        except Exception as e:
            logger.error(f"❌ ReRank失败: {str(e)}")
            # 失败时返回原始结果（取top_n）
            return chunks[:top_n]

    def generate_answer(self, question: str, chunks: list) -> str:
        """生成答案"""
        if not chunks:
            return "抱歉，没有找到相关资料。"

        # 构建context
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            speaker = metadata.get('speaker', '未知')
            date = metadata.get('date', '未知')
            group = metadata.get('group', '未知')
            text = chunk.get('text', '')

            context_parts.append(
                f"[文档{i}] 发言人: {speaker}, 党派: {group}, 日期: {date}\n{text}"
            )

        context = "\n\n".join(context_parts)

        # 构建prompt
        prompt = f"""请基于以下德国议会发言记录回答问题。

【问题】
{question}

【参考资料】
{context}

【回答要求】
1. 基于提供的资料进行总结和分析
2. 如果资料不足，请明确说明
3. 引用具体发言人、日期和党派
4. 保持客观和准确

请回答："""

        # 调用LLM (直接传prompt字符串，客户端会封装成消息)
        response = self.llm.invoke(prompt)
        # response已经是字符串类型
        return response

    def answer_question(self, question: str) -> dict:
        """完整的问答流程"""
        start_time = time.time()

        # 1. 参数提取
        logger.info("📋 步骤1: 参数提取")
        params = self.extract_parameters(question)

        # 2. 检索
        logger.info("📋 步骤2: 检索")
        retrieve_start = time.time()
        chunks = self.retrieve(question, params, top_k=20)
        retrieve_time = time.time() - retrieve_start

        # 3. ReRank
        logger.info("📋 步骤3: ReRank")
        rerank_start = time.time()
        reranked_chunks = self.rerank(question, chunks, top_n=10)
        rerank_time = time.time() - rerank_start

        # 4. 生成答案
        logger.info("📋 步骤4: 生成答案")
        generate_start = time.time()
        answer = self.generate_answer(question, reranked_chunks)
        generate_time = time.time() - generate_start

        total_time = time.time() - start_time

        return {
            "question": question,
            "params": params,
            "chunks_before_rerank": len(chunks),
            "chunks_after_rerank": len(reranked_chunks),
            "answer": answer,
            "timing": {
                "retrieve": retrieve_time,
                "rerank": rerank_time,
                "generate": generate_time,
                "total": total_time
            },
            "chunks": reranked_chunks
        }


def test_complete_workflow():
    """测试完整workflow"""

    logger.info("="*80)
    logger.info("🧪 完整Workflow测试（Pinecone + ReRank）")
    logger.info("="*80)

    # 初始化RAG
    rag = CompletePineconeRAG()

    # 测试问题
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
        logger.info(f"🔍 测试 {test_case['id']}: {test_case['type']}")
        logger.info(f"   问题: {test_case['question']}")
        logger.info(f"{'='*80}\n")

        try:
            result = rag.answer_question(test_case['question'])

            logger.info(f"✅ {test_case['id']} 完成")
            logger.info(f"   参数: {json.dumps(result['params'], ensure_ascii=False)}")
            logger.info(f"   检索前: {result['chunks_before_rerank']} 块")
            logger.info(f"   ReRank后: {result['chunks_after_rerank']} 块")
            logger.info(f"   检索耗时: {result['timing']['retrieve']:.2f}秒")
            logger.info(f"   ReRank耗时: {result['timing']['rerank']:.2f}秒")
            logger.info(f"   生成耗时: {result['timing']['generate']:.2f}秒")
            logger.info(f"   总耗时: {result['timing']['total']:.2f}秒")

            # 显示答案预览
            preview = result['answer'][:200] + "..." if len(result['answer']) > 200 else result['answer']
            logger.info(f"\n📝 答案预览:\n{preview}\n")

            # 收集结果
            results.append({
                "question_id": test_case['id'],
                "question_type": test_case['type'],
                **result
            })

        except Exception as e:
            logger.error(f"❌ {test_case['id']} 失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            results.append({
                "question_id": test_case['id'],
                "question_type": test_case['type'],
                "status": "failed",
                "error": str(e)
            })

    # 保存结果
    output_file = project_root / "complete_workflow_pinecone_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"\n✅ 结果已保存: {output_file}")

    # 生成对比报告
    generate_comparison_report(results)

    return results


def generate_comparison_report(results):
    """生成对比报告"""

    logger.info("📊 生成对比报告...")

    report_file = project_root / "WORKFLOW_PINECONE_COMPARISON.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 完整Workflow vs 简化脚本对比报告（Pinecone）\n\n")
        f.write("## 测试配置\n\n")
        f.write("- **测试时间**: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        f.write("- **数据范围**: 2015年德国议会数据\n")
        f.write("- **Vector DB**: Pinecone (german-bge index)\n")
        f.write("- **Embedding**: BGE-M3 (local, 1024-dim)\n")
        f.write("- **ReRank**: Cohere rerank-v3.5\n")
        f.write("- **LLM**: Gemini 2.5 Pro\n\n")

        f.write("## 完整Workflow流程\n\n")
        f.write("```\n")
        f.write("问题 → 参数提取 → 检索(top_k=20) → ReRank(top_n=10) → LLM生成答案\n")
        f.write("```\n\n")

        f.write("## 测试结果\n\n")

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

            f.write(f"#### 处理流程\n\n")
            f.write(f"- **提取参数**: {json.dumps(result['params'], ensure_ascii=False)}\n")
            f.write(f"- **检索**: {result['chunks_before_rerank']} 个文档块 (top_k=20, 带metadata过滤)\n")
            f.write(f"- **ReRank**: {result['chunks_after_rerank']} 个文档块 (top_n=10, Cohere rerank-v3.5)\n\n")

            f.write(f"#### 性能指标\n\n")
            f.write(f"- **检索耗时**: {result['timing']['retrieve']:.2f}秒\n")
            f.write(f"- **ReRank耗时**: {result['timing']['rerank']:.2f}秒\n")
            f.write(f"- **生成耗时**: {result['timing']['generate']:.2f}秒\n")
            f.write(f"- **总耗时**: {result['timing']['total']:.2f}秒\n\n")

            f.write(f"#### 完整Workflow答案\n\n")
            f.write(f"```\n{result['answer']}\n```\n\n")

            # 检索到的时间点分析
            if result['chunks']:
                dates = set()
                for chunk in result['chunks']:
                    metadata = chunk.get('metadata', {})
                    date = metadata.get('date', 'N/A')
                    if date != 'N/A':
                        dates.add(date)

                dates_sorted = sorted(list(dates))
                f.write(f"#### 检索到的时间点\n\n")
                f.write(f"- 共 {len(dates_sorted)} 个不同日期\n")
                for date in dates_sorted[:10]:
                    f.write(f"- {date}\n")
                if len(dates_sorted) > 10:
                    f.write(f"- ... 还有 {len(dates_sorted) - 10} 个日期\n")
                f.write("\n")

            f.write("---\n\n")

        f.write("## 性能对比\n\n")
        f.write("| 指标 | 完整Workflow | 简化脚本 |\n")
        f.write("|------|-------------|--------|\n")

        avg_total = sum(r['timing']['total'] for r in results if 'timing' in r) / len([r for r in results if 'timing' in r])
        f.write(f"| 平均总耗时 | {avg_total:.2f}秒 | ~30秒 |\n")

        avg_retrieve = sum(r['timing']['retrieve'] for r in results if 'timing' in r) / len([r for r in results if 'timing' in r])
        f.write(f"| 平均检索耗时 | {avg_retrieve:.2f}秒 | ~1秒 |\n")

        avg_rerank = sum(r['timing']['rerank'] for r in results if 'timing' in r) / len([r for r in results if 'timing' in r])
        f.write(f"| ReRank耗时 | {avg_rerank:.2f}秒 | 无 |\n")

        avg_chunks_before = sum(r['chunks_before_rerank'] for r in results if 'chunks_before_rerank' in r) / len([r for r in results if 'chunks_before_rerank' in r])
        avg_chunks_after = sum(r['chunks_after_rerank'] for r in results if 'chunks_after_rerank' in r) / len([r for r in results if 'chunks_after_rerank' in r])
        f.write(f"| 文档块数 | 检索{avg_chunks_before:.0f} → ReRank{avg_chunks_after:.0f} | 10个 |\n")

        f.write("| 参数提取 | ✅ 自动提取年份、党派、主题 | ❌ 无 |\n")
        f.write("| 元数据过滤 | ✅ 基于参数过滤 | ✅ 手动指定 |\n")
        f.write("| ReRank | ✅ Cohere rerank-v3.5 | ❌ 无 |\n\n")

        f.write("## 答案质量分析\n\n")
        f.write("### Q1: 难民政策总结问题\n\n")
        f.write("**简化脚本答案**提到: \"检索到的内容仅包含2015年5月和10月两个时间点\"\n\n")

        q1_result = next((r for r in results if r['question_id'] == 'Q1'), None)
        if q1_result and q1_result.get('chunks'):
            dates = set()
            for chunk in q1_result['chunks']:
                metadata = chunk.get('metadata', {})
                date = metadata.get('date', 'N/A')
                if date != 'N/A':
                    dates.add(date)

            dates_sorted = sorted(list(dates))
            f.write(f"**完整Workflow检索到的时间点**: {len(dates_sorted)} 个不同日期\n\n")
            for date in dates_sorted[:20]:
                f.write(f"- {date}\n")
            if len(dates_sorted) > 20:
                f.write(f"- ... 还有 {len(dates_sorted) - 20} 个日期\n")
            f.write("\n")

            # 检查月份分布
            months = set()
            for date in dates_sorted:
                if len(date.split('-')) >= 2:
                    month = date.split('-')[1]
                    months.add(month)

            f.write(f"**月份覆盖**: {sorted(list(months))}\n\n")

            if len(months) > 2:
                f.write("✅ **结论**: 完整workflow检索到了更多月份的数据，不仅限于5月和10月。\n\n")
            else:
                f.write("⚠️ **结论**: 完整workflow也主要检索到5月和10月的数据，可能这两个月确实是主要讨论时间。\n\n")

        f.write("## 总体评估\n\n")
        f.write("### 完整Workflow优势\n\n")
        f.write("1. **自动参数提取**: 无需手动指定年份、党派等过滤条件\n")
        f.write("2. **ReRank优化**: 使用Cohere API重新排序，提升相关性\n")
        f.write("3. **更大检索范围**: top_k=20后ReRank到10个，比直接top_k=10更全面\n")
        f.write("4. **更好的元数据过滤**: 基于提取的参数自动构建过滤条件\n\n")

        f.write("### 简化脚本优势\n\n")
        f.write("1. **更快速度**: 无ReRank和参数提取，直接检索+生成\n")
        f.write("2. **更简单**: 代码少，容易理解和调试\n")
        f.write("3. **适合简单问题**: 对于单一维度问题已足够\n\n")

        f.write("## 建议\n\n")
        f.write("- **生产环境**: 使用完整Workflow，答案质量更高\n")
        f.write("- **快速原型**: 使用简化脚本，开发调试更快\n")
        f.write("- **混合方案**: 简单问题用简化版，复杂问题用完整版\n\n")

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
