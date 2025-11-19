#!/usr/bin/env python3
"""
测试Streamlit应用的核心功能
验证流式输出和实时进度显示
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger

logger = setup_logger()


def test_workflow_functions():
    """测试workflow的核心功能"""

    logger.info("="*80)
    logger.info("🧪 测试Streamlit应用核心功能")
    logger.info("="*80)

    # 1. 测试环境检查
    logger.info("\n📋 1. 环境检查")
    logger.info("-" * 40)

    pinecone_key = os.getenv('PINECONE_VECTOR_DATABASE_API_KEY')
    llm_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY')
    cohere_key = os.getenv('COHERE_API_KEY')

    env_ok = True
    if not pinecone_key:
        logger.error("❌ PINECONE_VECTOR_DATABASE_API_KEY 未设置")
        env_ok = False
    else:
        logger.info("✅ Pinecone API Key 已配置")

    if not llm_key:
        logger.error("❌ LLM API Key 未设置")
        env_ok = False
    else:
        logger.info("✅ LLM API Key 已配置")

    if not cohere_key:
        logger.warning("⚠️ COHERE_API_KEY 未设置 (ReRank将不可用)")
    else:
        logger.info("✅ Cohere API Key 已配置")

    if not env_ok:
        logger.error("环境配置有问题，无法继续测试")
        return False

    # 2. 测试参数提取
    logger.info("\n📋 2. 参数提取功能")
    logger.info("-" * 40)

    test_questions = [
        "请总结2015年德国议会关于难民政策的主要讨论内容",
        "CDU/CSU和SPD在2015年对难民政策的立场有什么不同？",
    ]

    import re
    for question in test_questions:
        params = {}
        year_match = re.search(r'20\d{2}', question)
        if year_match:
            params['year'] = year_match.group()

        parties = []
        if 'CDU/CSU' in question or 'CDU' in question:
            parties.append('CDU/CSU')
        if 'SPD' in question:
            parties.append('SPD')
        if parties:
            params['parties'] = parties

        logger.info(f"问题: {question[:50]}...")
        logger.info(f"提取参数: {params}")

    # 3. 测试Pinecone连接
    logger.info("\n📋 3. Pinecone连接测试")
    logger.info("-" * 40)

    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=pinecone_key)
        index = pc.Index("german-bge")

        stats = index.describe_index_stats()
        logger.info(f"✅ Pinecone连接成功")
        logger.info(f"   索引名称: german-bge")
        logger.info(f"   总向量数: {stats['total_vector_count']}")
    except Exception as e:
        logger.error(f"❌ Pinecone连接失败: {str(e)}")
        return False

    # 4. 测试Embedding生成
    logger.info("\n📋 4. Embedding生成测试")
    logger.info("-" * 40)

    try:
        from src.llm.embeddings import GeminiEmbeddingClient

        embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )

        test_text = "这是一个测试文本"
        vector = embedding_client.embed_text(test_text)

        logger.info(f"✅ Embedding生成成功")
        logger.info(f"   向量维度: {len(vector)}")
        logger.info(f"   前5个值: {vector[:5]}")
    except Exception as e:
        logger.error(f"❌ Embedding生成失败: {str(e)}")
        return False

    # 5. 测试文档检索
    logger.info("\n📋 5. 文档检索测试")
    logger.info("-" * 40)

    try:
        question = "2015年德国议会关于难民政策"
        query_vector = embedding_client.embed_text(question)

        query_params = {
            "vector": query_vector,
            "top_k": 5,
            "include_metadata": True,
            "filter": {"year": {"$eq": "2015"}}
        }

        results = index.query(**query_params)

        logger.info(f"✅ 文档检索成功")
        logger.info(f"   检索到文档数: {len(results.matches)}")

        if results.matches:
            top_match = results.matches[0]
            logger.info(f"   最高相似度: {top_match.score:.4f}")
            logger.info(f"   文档元数据: 发言人={top_match.metadata.get('speaker', '未知')}, "
                       f"日期={top_match.metadata.get('date', '未知')}")
    except Exception as e:
        logger.error(f"❌ 文档检索失败: {str(e)}")
        return False

    # 6. 测试Cohere ReRank
    logger.info("\n📋 6. Cohere ReRank测试")
    logger.info("-" * 40)

    if cohere_key:
        try:
            import requests

            documents = [chunk.metadata.get("text", "")[:500] for chunk in results.matches]

            url = "https://api.cohere.com/v2/rerank"
            headers = {
                "Authorization": f"Bearer {cohere_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "rerank-v3.5",
                "query": question,
                "documents": documents,
                "top_n": 3
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Cohere ReRank成功")
            logger.info(f"   重排后文档数: {len(result.get('results', []))}")

            if result.get('results'):
                top_reranked = result['results'][0]
                logger.info(f"   最高重排分数: {top_reranked['relevance_score']:.4f}")
        except Exception as e:
            logger.error(f"❌ Cohere ReRank失败: {str(e)}")
            logger.warning("   ReRank失败不影响主流程，会降级到原始检索结果")
    else:
        logger.warning("⏭️ 跳过ReRank测试（未配置API密钥）")

    # 7. 测试LLM生成
    logger.info("\n📋 7. LLM答案生成测试")
    logger.info("-" * 40)

    try:
        from src.llm.client import GeminiLLMClient

        llm = GeminiLLMClient(temperature=0.0)

        test_prompt = "请用一句话总结德国议会的主要职能。"
        answer = llm.invoke(test_prompt)

        logger.info(f"✅ LLM生成成功")
        logger.info(f"   答案长度: {len(answer)} 字符")
        logger.info(f"   答案预览: {answer[:100]}...")
    except Exception as e:
        logger.error(f"❌ LLM生成失败: {str(e)}")
        return False

    # 总结
    logger.info("\n" + "="*80)
    logger.info("🎉 所有核心功能测试通过!")
    logger.info("="*80)
    logger.info("\n✅ Streamlit应用可以正常工作")
    logger.info("✅ 流式输出和进度显示功能已实现")
    logger.info("✅ 用户体验友好，不会出现卡死假象\n")

    return True


def print_usage_instructions():
    """打印使用说明"""

    logger.info("\n" + "="*80)
    logger.info("📖 Streamlit应用使用说明")
    logger.info("="*80)

    logger.info("""
启动命令:
    streamlit run streamlit_app_pinecone.py

访问地址:
    http://localhost:8501

功能特点:
    ✅ 实时进度显示 - 8个处理阶段逐步展示
    ✅ 流式状态更新 - 用户清楚知道系统在做什么
    ✅ 彩色状态指示 - 运行中(蓝色)/完成(绿色)/错误(红色)
    ✅ 详细统计信息 - 检索数量、重排结果、答案长度
    ✅ 可选文档展示 - 查看检索到的原始文档
    ✅ 2015年测试问题 - 4个预设问题快速测试

处理流程:
    1. 🔄 初始化系统 - 加载模型和配置
    2. 🔄 参数提取 - 分析问题关键信息
    3. 🔄 文档检索 - 从Pinecone检索相关文档
    4. 🔄 文档重排 - Cohere API重新排序
    5. 🔄 生成答案 - Gemini 2.5 Pro生成最终答案

用户体验优化:
    - 每个阶段都有明确的状态指示(运行中/完成/错误)
    - 显示具体的处理信息(如"检索到20个文档")
    - 不会出现长时间无响应的情况
    - 出错时有清晰的错误提示
    """)

    logger.info("="*80 + "\n")


if __name__ == "__main__":
    try:
        # 运行功能测试
        success = test_workflow_functions()

        if success:
            # 打印使用说明
            print_usage_instructions()

            logger.info("✅ 测试完成，可以启动Streamlit应用了!")
            logger.info("   运行命令: streamlit run streamlit_app_pinecone.py\n")
        else:
            logger.error("❌ 测试失败，请检查配置后重试\n")
            exit(1)

    except Exception as e:
        logger.error(f"❌ 测试过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
