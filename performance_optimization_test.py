#!/usr/bin/env python3
"""
批量处理性能优化测试
测试不同参数下的实际处理速度
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

def test_batch_embedding_performance():
    """测试批量embedding性能"""
    logger.info("🧠 测试BGE-M3批量embedding性能")
    
    try:
        from src.llm.embeddings import GeminiEmbeddingClient
        
        embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3", 
            dimensions=1024
        )
        
        # 生成测试文本
        test_texts = []
        for i in range(100):  # 测试100个文本
            text = f"这是第{i+1}个测试文本，用于验证BGE-M3批量embedding的性能。内容包括德国联邦议院的相关讨论和政治分析，确保文本长度和复杂度符合实际数据特征。"
            test_texts.append(text)
        
        # 测试不同批次大小
        batch_sizes = [16, 32, 64, 128]
        
        results = []
        
        for batch_size in batch_sizes:
            logger.info(f"🧪 测试批次大小: {batch_size}")
            
            start_time = time.time()
            vectors = embedding_client.embed_batch(
                test_texts,
                batch_size=batch_size,
                max_workers=4  # 保守并发数
            )
            embedding_time = time.time() - start_time
            
            speed = len(test_texts) / embedding_time
            results.append({
                'batch_size': batch_size,
                'time': embedding_time,
                'speed': speed,
                'vectors': len(vectors)
            })
            
            logger.info(f"   耗时: {embedding_time:.2f}秒")
            logger.info(f"   速度: {speed:.1f}条/秒")
            
            # 清理GPU内存
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        # 显示结果
        logger.info("📊 批量embedding性能对比:")
        logger.info("批次大小  |  耗时(秒)  |  速度(条/秒)")
        logger.info("-" * 40)
        for result in results:
            logger.info(f"   {result['batch_size']:3d}    |   {result['time']:6.2f}   |    {result['speed']:6.1f}")
        
        # 推荐最佳配置
        best_result = max(results, key=lambda x: x['speed'])
        logger.info(f"🎯 推荐配置: 批次大小 {best_result['batch_size']} (速度: {best_result['speed']:.1f}条/秒)")
        
        return best_result
        
    except Exception as e:
        logger.error(f"❌ 批量embedding测试失败: {str(e)}")
        return None

def test_batch_pinecone_performance(embedding_result):
    """测试批量Pinecone存储性能"""
    logger.info("📤 测试Pinecone批量存储性能")
    
    try:
        from pinecone import Pinecone
        from src.llm.embeddings import GeminiEmbeddingClient
        
        # 初始化
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        pc = Pinecone(api_key=api_key)
        index = pc.Index("german-bge")
        
        embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        
        # 生成测试数据
        test_texts = [
            f"Pinecone存储测试文本{i+1}：德国联邦议院的政治讨论和法律制定过程分析。"
            for i in range(50)  # 测试50个向量
        ]
        
        # 生成embeddings
        logger.info("🧠 生成测试embeddings")
        vectors = embedding_client.embed_batch(test_texts, batch_size=embedding_result['batch_size'])
        
        # 准备向量数据
        vector_data = []
        timestamp = int(time.time())
        for i, (text, vector) in enumerate(zip(test_texts, vectors)):
            vector_data.append({
                "id": f"perf_test_{timestamp}_{i}",
                "values": vector,
                "metadata": {
                    "text": text,
                    "test_type": "performance_batch",
                    "batch_id": timestamp
                }
            })
        
        # 测试不同批量存储大小
        upsert_batch_sizes = [10, 25, 50, 100]
        
        results = []
        
        for upsert_batch_size in upsert_batch_sizes:
            if upsert_batch_size > len(vector_data):
                continue
                
            logger.info(f"📦 测试存储批次大小: {upsert_batch_size}")
            
            # 取前N个向量测试
            test_vectors = vector_data[:upsert_batch_size]
            
            start_time = time.time()
            upsert_response = index.upsert(vectors=test_vectors)
            upsert_time = time.time() - start_time
            
            speed = len(test_vectors) / upsert_time if upsert_time > 0 else 0
            results.append({
                'batch_size': upsert_batch_size,
                'time': upsert_time, 
                'speed': speed,
                'response': upsert_response
            })
            
            logger.info(f"   耗时: {upsert_time:.2f}秒")
            logger.info(f"   速度: {speed:.1f}条/秒")
            logger.info(f"   结果: {upsert_response}")
            
            # 短暂等待避免API限制
            time.sleep(1)
        
        # 显示结果
        logger.info("📊 批量存储性能对比:")
        logger.info("批次大小  |  耗时(秒)  |  速度(条/秒)")
        logger.info("-" * 40)
        for result in results:
            logger.info(f"   {result['batch_size']:3d}    |   {result['time']:6.2f}   |    {result['speed']:6.1f}")
        
        # 推荐最佳配置
        best_result = max(results, key=lambda x: x['speed'])
        logger.info(f"🎯 推荐存储配置: 批次大小 {best_result['batch_size']} (速度: {best_result['speed']:.1f}条/秒)")
        
        # 清理测试数据
        logger.info("🧹 清理测试向量")
        test_ids = [v["id"] for v in vector_data]
        index.delete(ids=test_ids)
        
        return best_result
        
    except Exception as e:
        logger.error(f"❌ 批量存储测试失败: {str(e)}")
        return None

def calculate_optimized_migration_time(embedding_result, storage_result):
    """计算优化后的迁移时间"""
    logger.info("⏰ 计算优化后的迁移时间")
    
    # 预估数据量
    estimated_vectors = 79824 * 6  # 2015年 × 6年
    
    # 综合性能（考虑embedding和存储的平衡）
    embedding_speed = embedding_result['speed'] if embedding_result else 30
    storage_speed = storage_result['speed'] if storage_result else 20
    
    # 瓶颈速度（取较小值）
    bottleneck_speed = min(embedding_speed, storage_speed)
    
    # 加上数据处理开销（预估20%）
    effective_speed = bottleneck_speed * 0.8
    
    # 计算时间
    total_seconds = estimated_vectors / effective_speed
    total_hours = total_seconds / 3600
    
    logger.info("🎯 优化后时间预估:")
    logger.info(f"   预计向量数: {estimated_vectors:,}")
    logger.info(f"   Embedding速度: {embedding_speed:.1f}条/秒")  
    logger.info(f"   存储速度: {storage_speed:.1f}条/秒")
    logger.info(f"   瓶颈速度: {bottleneck_speed:.1f}条/秒")
    logger.info(f"   有效速度: {effective_speed:.1f}条/秒 (含处理开销)")
    logger.info(f"   预计总时间: {total_hours:.1f}小时 ({total_seconds/60:.0f}分钟)")
    
    # 提供不同场景
    scenarios = [
        ("保守估计", effective_speed * 0.7, "含网络延迟和重试"),
        ("乐观估计", effective_speed * 1.2, "最佳网络条件"),
        ("实际预期", effective_speed, "综合考虑各种因素")
    ]
    
    logger.info("📊 不同场景预估:")
    for name, speed, desc in scenarios:
        hours = estimated_vectors / speed / 3600
        logger.info(f"   {name}: {hours:.1f}小时 ({desc})")
    
    return total_hours

def main():
    """主测试函数"""
    logger.info("🚀 开始批量处理性能优化测试")
    logger.info("=" * 60)
    
    # 测试1: 批量embedding性能
    embedding_result = test_batch_embedding_performance()
    
    if not embedding_result:
        logger.error("❌ Embedding测试失败，无法继续")
        return 1
    
    logger.info("-" * 40)
    
    # 测试2: 批量存储性能  
    storage_result = test_batch_pinecone_performance(embedding_result)
    
    if not storage_result:
        logger.error("❌ 存储测试失败")
        return 1
    
    logger.info("-" * 40)
    
    # 测试3: 计算优化时间
    optimized_hours = calculate_optimized_migration_time(embedding_result, storage_result)
    
    logger.info("=" * 60)
    logger.info("🎉 性能优化测试完成！")
    logger.info(f"📈 预计迁移时间可缩短至: {optimized_hours:.1f}小时")
    
    return 0

if __name__ == "__main__":
    exit(main())
