#!/usr/bin/env python3
"""
Pinecone RAG系统端到端测试
验证2015年数据的完整RAG流程：检索 -> 生成答案
测试不同类型的问题：总结类、对比类、观点类
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
from pinecone import Pinecone

logger = setup_logger()


class SimplePineconeRAG:
    """简化的Pinecone RAG系统"""

    def __init__(self):
        """初始化RAG系统"""
        logger.info("🔧 初始化Pinecone RAG系统")

        # 初始化Embedding客户端
        self.embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        logger.info("✅ BGE-M3 Embedding客户端初始化完成")

        # 初始化Pinecone
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index("german-bge")
        logger.info("✅ Pinecone客户端初始化完成")

        # 初始化LLM客户端（使用项目中的GeminiLLMClient）
        from src.llm.client import GeminiLLMClient
        self.llm = GeminiLLMClient(temperature=0.0)
        logger.info("✅ Gemini LLM客户端初始化完成")

    def retrieve(self, question: str, top_k: int = 10, year_filter: str = None):
        """
        检索相关文档

        Args:
            question: 问题
            top_k: 检索数量
            year_filter: 年份过滤（例如 "2015"）

        Returns:
            检索结果列表
        """
        logger.info(f"🔍 检索问题: {question}")
        start_time = time.time()

        # 生成问题的embedding
        query_vector = self.embedding_client.embed_text(question)

        # 准备过滤条件
        filter_dict = {}
        if year_filter:
            filter_dict["year"] = {"$eq": year_filter}

        # 执行Pinecone查询
        query_params = {
            "vector": query_vector,
            "top_k": top_k,
            "include_metadata": True
        }
        if filter_dict:
            query_params["filter"] = filter_dict

        results = self.index.query(**query_params)

        retrieval_time = time.time() - start_time

        # 提取结果
        chunks = []
        for match in results.matches:
            chunks.append({
                "id": match.id,
                "score": match.score,
                "text": match.metadata.get("text", ""),
                "speaker": match.metadata.get("speaker", ""),
                "date": match.metadata.get("date", ""),
                "group": match.metadata.get("group", ""),
                "metadata": match.metadata
            })

        logger.info(f"✅ 检索完成: {len(chunks)}个结果，耗时{retrieval_time:.2f}秒")

        return chunks, retrieval_time

    def generate_answer(self, question: str, chunks: list):
        """
        基于检索结果生成答案

        Args:
            question: 问题
            chunks: 检索到的文档块

        Returns:
            生成的答案
        """
        logger.info(f"🧠 生成答案: {question}")
        start_time = time.time()

        # 构建上下文
        context_parts = []
        for i, chunk in enumerate(chunks[:5], 1):  # 只使用top 5
            context_parts.append(
                f"[文档{i}]\n"
                f"发言人: {chunk['speaker']}\n"
                f"日期: {chunk['date']}\n"
                f"党派: {chunk['group']}\n"
                f"相似度: {chunk['score']:.4f}\n"
                f"内容: {chunk['text'][:500]}\n"
            )

        context = "\n\n".join(context_parts)

        # 构建prompt
        prompt = f"""你是一个专业的德国议会演讲分析助手。请基于以下检索到的德国议会演讲内容，回答用户的问题。

问题: {question}

检索到的相关演讲内容:
{context}

请根据上述内容，用中文提供一个全面、准确的回答。要求：
1. 如果检索内容充分，给出详细回答
2. 如果检索内容不足，说明现有材料的局限性
3. 引用具体的发言人和日期
4. 保持客观和准确

回答:"""

        # 调用LLM生成答案
        try:
            answer = self.llm.invoke(prompt)
            generation_time = time.time() - start_time

            logger.info(f"✅ 答案生成完成，耗时{generation_time:.2f}秒")
            return answer, generation_time

        except Exception as e:
            logger.error(f"❌ 答案生成失败: {str(e)}")
            return f"答案生成失败: {str(e)}", time.time() - start_time

    def answer_question(self, question: str, year_filter: str = None):
        """
        完整的RAG问答流程

        Args:
            question: 问题
            year_filter: 年份过滤

        Returns:
            答案和性能指标
        """
        total_start = time.time()

        # 检索
        chunks, retrieval_time = self.retrieve(question, top_k=10, year_filter=year_filter)

        if not chunks:
            return {
                "question": question,
                "answer": "未找到相关文档",
                "retrieval_count": 0,
                "retrieval_time": retrieval_time,
                "generation_time": 0,
                "total_time": time.time() - total_start
            }

        # 生成答案
        answer, generation_time = self.generate_answer(question, chunks)

        total_time = time.time() - total_start

        return {
            "question": question,
            "answer": answer,
            "retrieval_count": len(chunks),
            "top_scores": [c["score"] for c in chunks[:3]],
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "total_time": total_time
        }


def test_rag_system():
    """测试RAG系统"""
    logger.info("🚀 开始Pinecone RAG端到端测试")
    logger.info("=" * 80)

    # 初始化RAG系统
    rag = SimplePineconeRAG()

    # 测试问题集（不同类型）
    test_cases = [
        {
            "name": "总结类问题",
            "question": "请总结2015年德国议会关于难民政策的主要讨论内容",
            "year_filter": "2015"
        },
        {
            "name": "对比类问题",
            "question": "CDU/CSU和SPD在2015年对难民政策的立场有什么不同？",
            "year_filter": "2015"
        },
        {
            "name": "观点类问题",
            "question": "2015年德国议会议员对欧盟一体化的主要观点是什么？",
            "year_filter": "2015"
        },
        {
            "name": "事实查询问题",
            "question": "2015年德国议会有哪些重要法案被讨论？",
            "year_filter": "2015"
        }
    ]

    results = []

    # 测试每个问题
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"📝 测试 {i}/{len(test_cases)}: {test_case['name']}")
        print(f"   问题: {test_case['question']}")
        print('='*80)

        try:
            result = rag.answer_question(
                question=test_case["question"],
                year_filter=test_case.get("year_filter")
            )

            results.append({
                "test_name": test_case["name"],
                **result
            })

            # 显示结果
            print(f"\n📊 性能指标:")
            print(f"   检索时间: {result['retrieval_time']:.2f}秒")
            print(f"   生成时间: {result['generation_time']:.2f}秒")
            print(f"   总耗时: {result['total_time']:.2f}秒")
            print(f"   检索文档数: {result['retrieval_count']}")
            if result['top_scores']:
                print(f"   Top-3相似度: {[f'{s:.4f}' for s in result['top_scores']]}")

            print(f"\n📄 生成答案:")
            print(result['answer'])
            print()

        except Exception as e:
            logger.error(f"❌ 测试失败: {str(e)}")
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    # 总结统计
    print(f"\n{'='*80}")
    print("📊 测试总结统计")
    print('='*80)

    if results:
        avg_retrieval_time = sum(r['retrieval_time'] for r in results) / len(results)
        avg_generation_time = sum(r['generation_time'] for r in results) / len(results)
        avg_total_time = sum(r['total_time'] for r in results) / len(results)
        avg_retrieval_count = sum(r['retrieval_count'] for r in results) / len(results)

        print(f"✅ 成功测试: {len(results)}/{len(test_cases)}")
        print(f"\n⏱️  平均性能:")
        print(f"   检索时间: {avg_retrieval_time:.2f}秒")
        print(f"   生成时间: {avg_generation_time:.2f}秒")
        print(f"   总耗时: {avg_total_time:.2f}秒")
        print(f"   检索文档数: {avg_retrieval_count:.1f}")

        # 保存结果到JSON
        output_file = project_root / "rag_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 详细结果已保存到: {output_file}")

    else:
        print(f"❌ 所有测试失败")
        return 1

    print(f"\n{'='*80}")
    print("🎉 Pinecone RAG端到端测试完成！")
    print('='*80)

    return 0


def main():
    """主函数"""
    try:
        return test_rag_system()
    except Exception as e:
        logger.error(f"❌ 测试程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
