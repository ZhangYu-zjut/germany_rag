#!/usr/bin/env python3
"""
手动检索测试 - 展示检索到的实际内容
用于评估2015年数据的检索质量
"""

import os
import sys
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


def retrieve_and_display(question: str, year_filter: str = None, top_k: int = 5):
    """
    检索并展示结果

    Args:
        question: 问题
        year_filter: 年份过滤
        top_k: 返回结果数
    """
    print("="*100)
    print(f"🔍 问题: {question}")
    if year_filter:
        print(f"📅 年份过滤: {year_filter}")
    print("="*100)

    # 初始化
    embedding_client = GeminiEmbeddingClient(
        embedding_mode="local",
        model_name="BAAI/bge-m3",
        dimensions=1024
    )

    api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
    pc = Pinecone(api_key=api_key)
    index = pc.Index("german-bge")

    # 生成query向量
    query_vector = embedding_client.embed_text(question)

    # 准备过滤条件
    query_params = {
        "vector": query_vector,
        "top_k": top_k,
        "include_metadata": True
    }

    if year_filter:
        query_params["filter"] = {"year": {"$eq": year_filter}}

    # 执行检索
    results = index.query(**query_params)

    print(f"\n📊 检索统计:")
    print(f"   返回结果数: {len(results.matches)}")

    # 展示每个结果
    for i, match in enumerate(results.matches, 1):
        print(f"\n{'─'*100}")
        print(f"📄 结果 {i}:")
        print(f"   相似度分数: {match.score:.4f}")
        print(f"   文档ID: {match.id}")

        metadata = match.metadata
        print(f"\n   📋 元数据:")
        print(f"      发言人: {metadata.get('speaker', 'N/A')}")
        print(f"      日期: {metadata.get('date', 'N/A')}")
        print(f"      党派: {metadata.get('group', 'N/A')}")
        print(f"      党派(中文): {metadata.get('group_chinese', 'N/A')}")
        print(f"      会议: {metadata.get('session', 'N/A')}")
        print(f"      立法期: {metadata.get('lp', 'N/A')}")

        # 展示文本内容
        text = metadata.get('text', '')
        print(f"\n   📝 演讲内容 (前800字符):")
        print(f"      {text[:800]}")
        if len(text) > 800:
            print(f"      ... (共{len(text)}字符)")

    print(f"\n{'='*100}\n")


def main():
    """主函数"""
    print("\n🚀 2015年数据检索质量测试")
    print("="*100)

    # 测试案例
    test_cases = [
        {
            "question": "请总结2015年德国议会关于难民政策的主要讨论内容",
            "year": "2015",
            "description": "总结类问题 - 难民政策"
        },
        {
            "question": "CDU/CSU和SPD在2015年对难民政策的立场有什么不同？",
            "year": "2015",
            "description": "对比类问题 - 党派立场对比"
        },
        {
            "question": "2015年德国议会议员对欧盟一体化的主要观点是什么？",
            "year": "2015",
            "description": "观点类问题 - 欧盟一体化"
        },
        {
            "question": "2015年德国议会有哪些重要法案被讨论？",
            "year": "2015",
            "description": "事实查询问题 - 重要法案"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n📋 测试案例 {i}/{len(test_cases)}: {test_case['description']}")
        retrieve_and_display(
            question=test_case['question'],
            year_filter=test_case['year'],
            top_k=5
        )

        # 暂停以便查看
        if i < len(test_cases):
            input("按Enter继续下一个测试...")

    print("\n🎉 所有测试完成！")


if __name__ == "__main__":
    main()
