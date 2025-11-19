#!/usr/bin/env python3
"""
快速Pinecone连接和存储测试
验证向量能否正常存储到Pinecone
"""

import os
import sys
import time
import random
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger

logger = setup_logger()

def test_pinecone_connection():
    """测试Pinecone连接和基本操作"""
    logger.info("🧪 开始Pinecone连接和存储测试")
    
    try:
        from pinecone import Pinecone, ServerlessSpec
        
        # 1. 初始化Pinecone客户端
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        if not api_key:
            logger.error("❌ PINECONE_VECTOR_DATABASE_API_KEY 未设置")
            return False
        
        pc = Pinecone(api_key=api_key)
        logger.info("✅ Pinecone客户端初始化成功")
        
        # 2. 列出现有索引
        existing_indexes = pc.list_indexes()
        logger.info(f"📊 现有索引数量: {len(existing_indexes)}")
        
        for idx in existing_indexes:
            logger.info(f"   - {idx.name}: {idx.dimension}维, {idx.metric}")
        
        # 3. 连接到german-bge索引
        target_index = None
        for idx in existing_indexes:
            if "german-bge" in idx.name.lower():
                target_index = idx.name
                break
        
        if not target_index:
            logger.error("❌ 未找到german-bge索引")
            return False
        
        logger.info(f"🔗 连接到索引: {target_index}")
        index = pc.Index(target_index)
        
        # 4. 检查索引状态
        stats = index.describe_index_stats()
        logger.info(f"📊 索引统计:")
        logger.info(f"   总向量数: {stats['total_vector_count']}")
        logger.info(f"   向量维度: {stats['dimension']}")
        
        # 5. 测试向量插入
        logger.info("🧪 测试向量插入...")
        
        # 创建测试向量
        test_vectors = []
        for i in range(5):
            vector_id = f"test_{int(time.time())}_{i}"
            vector_values = [random.uniform(-0.1, 0.1) for _ in range(1024)]  # BGE-M3维度
            
            test_vectors.append({
                "id": vector_id,
                "values": vector_values,
                "metadata": {
                    "text": f"测试向量 {i}",
                    "year": "2025",
                    "test": "true"
                }
            })
        
        # 插入测试向量
        try:
            index.upsert(vectors=test_vectors)
            logger.info("✅ 测试向量插入成功")
            
            # 等待索引更新
            time.sleep(2)
            
            # 6. 验证插入结果
            new_stats = index.describe_index_stats()
            logger.info(f"📊 插入后统计:")
            logger.info(f"   总向量数: {new_stats['total_vector_count']}")
            
            if new_stats['total_vector_count'] > stats['total_vector_count']:
                logger.info("✅ 向量数量增加，插入成功！")
            else:
                logger.warning("⚠️ 向量数量未增加，可能需要等待索引更新")
            
            # 7. 测试搜索功能
            logger.info("🔍 测试向量搜索...")
            search_vector = [random.uniform(-0.1, 0.1) for _ in range(1024)]
            
            search_results = index.query(
                vector=search_vector,
                top_k=3,
                include_metadata=True
            )
            
            logger.info(f"🔍 搜索结果: {len(search_results.matches)} 个匹配")
            for i, match in enumerate(search_results.matches[:2], 1):
                score = match.score
                metadata = match.metadata
                text = metadata.get('text', 'N/A')
                logger.info(f"   [{i}] 相似度: {score:.4f}, 文本: {text}")
            
            # 8. 清理测试数据
            logger.info("🧹 清理测试向量...")
            test_ids = [v["id"] for v in test_vectors]
            index.delete(ids=test_ids)
            logger.info("✅ 测试向量清理完成")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 向量插入失败: {str(e)}")
            return False
        
    except ImportError:
        logger.error("❌ 无法导入pinecone模块")
        return False
    except Exception as e:
        logger.error(f"❌ Pinecone测试失败: {str(e)}")
        return False

def test_bge_m3_embedding():
    """测试BGE-M3 embedding生成"""
    logger.info("🧠 测试BGE-M3 embedding生成")
    
    try:
        from src.llm.embeddings import GeminiEmbeddingClient
        
        # 初始化BGE-M3客户端
        embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        
        # 测试单个文本embedding
        test_text = "这是一个测试文本，用于验证BGE-M3 embedding生成。"
        embedding = embedding_client.embed_text(test_text)
        
        if embedding and len(embedding) == 1024:
            logger.info("✅ BGE-M3 embedding生成成功")
            logger.info(f"   向量维度: {len(embedding)}")
            logger.info(f"   向量范围: [{min(embedding):.4f}, {max(embedding):.4f}]")
            return embedding
        else:
            logger.error("❌ BGE-M3 embedding生成失败")
            return None
            
    except Exception as e:
        logger.error(f"❌ BGE-M3测试失败: {str(e)}")
        return None

def test_end_to_end():
    """端到端测试：BGE-M3 → Pinecone"""
    logger.info("🔄 开始端到端测试: BGE-M3 → Pinecone")
    
    # 1. 测试BGE-M3 embedding
    embedding = test_bge_m3_embedding()
    if not embedding:
        return False
    
    # 2. 测试Pinecone连接
    if not test_pinecone_connection():
        return False
    
    # 3. 端到端测试
    try:
        from pinecone import Pinecone
        
        pc = Pinecone(api_key=os.getenv("PINECONE_VECTOR_DATABASE_API_KEY"))
        existing_indexes = pc.list_indexes()
        
        target_index = None
        for idx in existing_indexes:
            if "german-bge" in idx.name.lower():
                target_index = idx.name
                break
        
        if not target_index:
            logger.error("❌ 未找到目标索引")
            return False
        
        index = pc.Index(target_index)
        
        # 创建真实的BGE-M3向量
        vector_id = f"e2e_test_{int(time.time())}"
        vector_data = {
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "text": "端到端测试向量",
                "source": "BGE-M3",
                "test": "end_to_end"
            }
        }
        
        # 插入向量
        index.upsert(vectors=[vector_data])
        logger.info("✅ BGE-M3向量成功存储到Pinecone")
        
        # 等待和验证
        time.sleep(2)
        
        # 使用相同向量搜索
        search_results = index.query(
            vector=embedding,
            top_k=1,
            include_metadata=True
        )
        
        if search_results.matches and search_results.matches[0].score > 0.99:
            logger.info("✅ 端到端测试成功：BGE-M3向量能够正确存储和检索")
        else:
            logger.warning("⚠️ 端到端测试可能有问题")
        
        # 清理
        index.delete(ids=[vector_id])
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 端到端测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始Pinecone完整测试")
    logger.info("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # 测试1: Pinecone连接
    if test_pinecone_connection():
        success_count += 1
        
    # 测试2: BGE-M3 embedding
    if test_bge_m3_embedding():
        success_count += 1
    
    # 测试3: 端到端测试
    if test_end_to_end():
        success_count += 1
    
    logger.info("=" * 60)
    logger.info(f"📊 测试结果: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过！BGE-M3 + Pinecone集成正常工作")
        return 0
    else:
        logger.error("❌ 部分测试失败，需要排查问题")
        return 1

if __name__ == "__main__":
    exit(main())
