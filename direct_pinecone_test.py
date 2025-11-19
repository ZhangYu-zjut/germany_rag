#!/usr/bin/env python3
"""
直接测试BGE-M3 → Pinecone完整流程
使用实际存在的索引
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

def test_direct_pinecone_storage():
    """直接测试Pinecone存储流程"""
    logger.info("🚀 直接测试BGE-M3 → Pinecone存储流程")
    
    try:
        # 1. 初始化BGE-M3 embedding
        from src.llm.embeddings import GeminiEmbeddingClient
        
        embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        logger.info("✅ BGE-M3客户端初始化成功")
        
        # 2. 初始化Pinecone
        from pinecone import Pinecone
        
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        pc = Pinecone(api_key=api_key)
        
        # 3. 获取实际索引
        existing_indexes = pc.list_indexes()
        if not existing_indexes:
            logger.error("❌ 没有找到任何Pinecone索引")
            return False
        
        # 使用第一个索引（实际存在的）
        target_index = existing_indexes[0].name
        logger.info(f"🎯 使用索引: {target_index}")
        logger.info(f"   维度: {existing_indexes[0].dimension}")
        logger.info(f"   相似度算法: {existing_indexes[0].metric}")
        
        index = pc.Index(target_index)
        
        # 4. 检查索引当前状态
        stats = index.describe_index_stats()
        initial_count = stats['total_vector_count']
        logger.info(f"📊 索引当前状态:")
        logger.info(f"   总向量数: {initial_count}")
        logger.info(f"   向量维度: {stats['dimension']}")
        
        # 5. 测试BGE-M3 embedding生成
        test_texts = [
            "这是第一个德语测试文本，用于验证BGE-M3 embedding。",
            "Das ist der zweite deutsche Testtext für die Verifizierung.",
            "德国联邦议院是德国的最高立法机构，负责制定法律。",
            "Die Bundestagsabgeordneten vertreten die Interessen der Bürger.",
            "测试文本：关于德国政治体系的讨论和分析。"
        ]
        
        logger.info(f"🧠 开始生成{len(test_texts)}个文本的embedding")
        start_time = time.time()
        
        vectors = embedding_client.embed_batch(test_texts, batch_size=5)
        
        embedding_time = time.time() - start_time
        logger.info(f"✅ BGE-M3 embedding生成完成")
        logger.info(f"   生成时间: {embedding_time:.2f}秒")
        logger.info(f"   向量数量: {len(vectors)}")
        logger.info(f"   每个向量维度: {len(vectors[0])}")
        
        # 6. 准备向量数据
        test_vectors = []
        for i, (text, vector) in enumerate(zip(test_texts, vectors)):
            vector_id = f"direct_test_{int(time.time())}_{i}"
            test_vectors.append({
                "id": vector_id,
                "values": vector,
                "metadata": {
                    "text": text,
                    "test_type": "direct_bge_m3",
                    "timestamp": int(time.time()),
                    "batch_id": f"direct_test_{int(time.time())}"
                }
            })
        
        # 7. 批量插入向量到Pinecone
        logger.info(f"📤 开始插入{len(test_vectors)}个向量到Pinecone")
        upsert_start = time.time()
        
        upsert_response = index.upsert(vectors=test_vectors)
        
        upsert_time = time.time() - upsert_start
        logger.info(f"✅ 向量插入完成")
        logger.info(f"   插入时间: {upsert_time:.2f}秒")
        logger.info(f"   插入结果: {upsert_response}")
        
        # 8. 等待索引更新
        logger.info("⏳ 等待索引更新（5秒）")
        time.sleep(5)
        
        # 9. 验证插入结果
        new_stats = index.describe_index_stats()
        final_count = new_stats['total_vector_count']
        
        logger.info(f"📊 插入后索引状态:")
        logger.info(f"   总向量数: {final_count}")
        logger.info(f"   新增向量: {final_count - initial_count}")
        
        if final_count > initial_count:
            logger.info("🎉 向量成功存储到Pinecone！")
        else:
            logger.warning("⚠️ 向量数量未增加，可能需要更长时间同步")
        
        # 10. 测试向量搜索功能
        logger.info("🔍 测试向量搜索功能")
        
        # 使用第一个向量进行相似搜索
        search_vector = vectors[0]
        search_results = index.query(
            vector=search_vector,
            top_k=3,
            include_metadata=True
        )
        
        logger.info(f"🔍 搜索结果: {len(search_results.matches)} 个匹配")
        for i, match in enumerate(search_results.matches, 1):
            score = match.score
            metadata = match.metadata or {}
            text = metadata.get('text', 'N/A')[:50] + "..." if len(metadata.get('text', '')) > 50 else metadata.get('text', 'N/A')
            
            logger.info(f"   [{i}] 相似度: {score:.4f}")
            logger.info(f"       文本: {text}")
            logger.info(f"       ID: {match.id}")
        
        # 11. 性能统计
        total_time = embedding_time + upsert_time
        logger.info("📈 性能统计:")
        logger.info(f"   Embedding生成: {embedding_time:.2f}秒 ({len(test_texts)/embedding_time:.1f} 条/秒)")
        logger.info(f"   Pinecone存储: {upsert_time:.2f}秒")
        logger.info(f"   总处理时间: {total_time:.2f}秒")
        
        # 12. 清理测试数据
        logger.info("🧹 清理测试向量")
        test_ids = [v["id"] for v in test_vectors]
        index.delete(ids=test_ids)
        
        logger.info("✅ 测试完成！BGE-M3 → Pinecone完整流程工作正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始BGE-M3 → Pinecone直接测试")
    logger.info("=" * 60)
    
    success = test_direct_pinecone_storage()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 完整流程测试成功！可以开始大规模迁移")
        return 0
    else:
        logger.error("❌ 流程测试失败")
        return 1

if __name__ == "__main__":
    exit(main())
