#!/usr/bin/env python3
"""
验证german-bge索引状态并实际上传测试数据
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger

logger = setup_logger()

def verify_german_bge_status():
    """验证german-bge索引的实际状态"""
    logger.info("🔍 验证german-bge索引实际状态")
    
    try:
        from pinecone import Pinecone
        
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        pc = Pinecone(api_key=api_key)
        
        # 连接索引
        index = pc.Index("german-bge")
        
        # 获取详细状态
        stats = index.describe_index_stats()
        
        logger.info("📊 german-bge索引详细状态:")
        logger.info(f"   总向量数: {stats['total_vector_count']}")
        logger.info(f"   向量维度: {stats['dimension']}")
        logger.info(f"   命名空间数: {len(stats.get('namespaces', {}))}")
        
        # 显示命名空间详情
        namespaces = stats.get('namespaces', {})
        if namespaces:
            logger.info("   命名空间详情:")
            for ns_name, ns_info in namespaces.items():
                logger.info(f"     - {ns_name}: {ns_info.get('vector_count', 0)}个向量")
        else:
            logger.info("   没有命名空间数据")
        
        # 尝试随机查询验证是否真的为空
        try:
            query_result = index.query(
                vector=[0.1] * 1024,  # 随机向量
                top_k=1,
                include_metadata=True
            )
            
            if query_result.matches:
                logger.info(f"🔍 查询到{len(query_result.matches)}个向量:")
                for match in query_result.matches:
                    logger.info(f"   - ID: {match.id}")
                    logger.info(f"   - 分数: {match.score}")
                    logger.info(f"   - 元数据: {match.metadata}")
            else:
                logger.info("🔍 查询结果: 确实没有任何向量")
                
        except Exception as e:
            logger.error(f"❌ 查询测试失败: {str(e)}")
        
        return stats['total_vector_count']
        
    except Exception as e:
        logger.error(f"❌ 获取索引状态失败: {str(e)}")
        return None

def upload_real_data():
    """实际上传数据到german-bge索引"""
    logger.info("📤 实际上传数据到german-bge索引")
    
    try:
        from pinecone import Pinecone
        from src.llm.embeddings import GeminiEmbeddingClient
        
        # 初始化客户端
        embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        pc = Pinecone(api_key=api_key)
        index = pc.Index("german-bge")
        
        # 准备真实测试数据
        test_documents = [
            {
                "text": "德国联邦议院（Deutscher Bundestag）是德国联邦共和国的议会下院，也是主要立法机构。联邦议院由德国公民直接选举产生，通常每四年举行一次选举。",
                "metadata": {
                    "source": "德国政治体系介绍",
                    "topic": "联邦议院",
                    "year": "2025",
                    "language": "德语"
                }
            },
            {
                "text": "Die Bundesregierung ist das oberste Exekutivorgan der Bundesrepublik Deutschland. Sie besteht aus dem Bundeskanzler und den Bundesministern.",
                "metadata": {
                    "source": "German Government Structure",
                    "topic": "Bundesregierung", 
                    "year": "2025",
                    "language": "德语"
                }
            },
            {
                "text": "德国的选举制度采用混合制，结合了比例代表制和多数制的特点。选民有两票：第一票投给选区候选人，第二票投给政党名单。",
                "metadata": {
                    "source": "德国选举制度分析",
                    "topic": "选举制度",
                    "year": "2025", 
                    "language": "中文"
                }
            }
        ]
        
        # 记录上传前状态
        before_stats = index.describe_index_stats()
        before_count = before_stats['total_vector_count']
        logger.info(f"📊 上传前向量数: {before_count}")
        
        # 生成embeddings并上传
        vectors_to_upload = []
        timestamp = int(time.time())
        
        for i, doc in enumerate(test_documents):
            logger.info(f"🧠 处理第{i+1}个文档")
            
            # 生成embedding
            vector = embedding_client.embed_text(doc["text"])
            
            # 准备向量数据
            vector_data = {
                "id": f"real_test_{timestamp}_{i}",
                "values": vector,
                "metadata": {
                    **doc["metadata"],
                    "text": doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"],
                    "upload_timestamp": timestamp,
                    "test_type": "real_verification"
                }
            }
            
            vectors_to_upload.append(vector_data)
            logger.info(f"   ✅ 向量ID: {vector_data['id']}")
            logger.info(f"   📝 文本预览: {doc['text'][:50]}...")
        
        # 批量上传
        logger.info(f"📤 开始上传{len(vectors_to_upload)}个向量")
        start_time = time.time()
        
        upsert_response = index.upsert(vectors=vectors_to_upload)
        
        upload_time = time.time() - start_time
        logger.info(f"✅ 上传完成")
        logger.info(f"   耗时: {upload_time:.2f}秒")
        logger.info(f"   结果: {upsert_response}")
        
        # 等待索引更新
        logger.info("⏳ 等待索引更新（5秒）")
        time.sleep(5)
        
        # 验证上传结果
        after_stats = index.describe_index_stats()
        after_count = after_stats['total_vector_count']
        
        logger.info(f"📊 上传后状态:")
        logger.info(f"   上传前: {before_count}个向量")
        logger.info(f"   上传后: {after_count}个向量")
        logger.info(f"   增加: {after_count - before_count}个向量")
        
        if after_count > before_count:
            logger.info("🎉 数据上传成功！索引向量数确实增加了")
            
            # 测试搜索验证
            logger.info("🔍 验证搜索功能")
            
            # 使用第一个向量搜索
            search_vector = vectors_to_upload[0]["values"]
            search_results = index.query(
                vector=search_vector,
                top_k=5,
                include_metadata=True
            )
            
            logger.info(f"🔍 搜索到{len(search_results.matches)}个结果:")
            for j, match in enumerate(search_results.matches, 1):
                logger.info(f"   [{j}] ID: {match.id}")
                logger.info(f"       相似度: {match.score:.4f}")
                logger.info(f"       文本: {match.metadata.get('text', 'N/A')[:80]}...")
                
            return True
        else:
            logger.error("❌ 数据上传失败！向量数没有增加")
            return False
            
    except Exception as e:
        logger.error(f"❌ 数据上传失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始验证german-bge索引并上传真实数据")
    logger.info("=" * 60)
    
    # 步骤1: 验证索引状态
    vector_count = verify_german_bge_status()
    
    if vector_count is None:
        logger.error("❌ 无法访问german-bge索引")
        return 1
    
    logger.info("-" * 40)
    
    # 步骤2: 上传真实数据
    upload_success = upload_real_data()
    
    logger.info("=" * 60)
    
    if upload_success:
        logger.info("🎉 验证完成！数据确实成功上传到german-bge索引")
        logger.info("💡 现在可以确认链路完全正常工作")
        return 0
    else:
        logger.error("❌ 验证失败！需要排查问题")
        return 1

if __name__ == "__main__":
    exit(main())
