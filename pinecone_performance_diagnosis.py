#!/usr/bin/env python3
"""
Pinecone性能诊断工具
分析影响Pinecone存储性能的各种因素
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger

logger = setup_logger()

def check_network_conditions():
    """检查网络条件和代理设置"""
    logger.info("🌐 网络条件诊断")
    
    # 1. 检查代理设置
    http_proxy = os.environ.get('http_proxy')
    https_proxy = os.environ.get('https_proxy')
    
    logger.info("🔍 代理设置检查:")
    logger.info(f"   HTTP代理: {http_proxy if http_proxy else '未设置'}")
    logger.info(f"   HTTPS代理: {https_proxy if https_proxy else '未设置'}")
    
    if http_proxy or https_proxy:
        logger.warning("⚠️ 发现代理设置，这可能严重影响Pinecone性能!")
        logger.info("💡 建议: 暂时禁用代理测试性能差异")
    
    # 2. 网络延迟测试
    logger.info("🏃 网络延迟测试:")
    test_urls = [
        ("Pinecone API", "https://api.pinecone.io"),
        ("Google DNS", "https://8.8.8.8"),
        ("Cloudflare DNS", "https://1.1.1.1"),
    ]
    
    for name, url in test_urls:
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            latency = (time.time() - start_time) * 1000
            logger.info(f"   {name}: {latency:.0f}ms (状态: {response.status_code})")
        except Exception as e:
            logger.error(f"   {name}: 连接失败 ({str(e)})")
    
    # 3. 带宽估测
    logger.info("📊 粗略带宽测试:")
    try:
        test_url = "https://httpbin.org/bytes/1024"  # 下载1KB数据
        start_time = time.time()
        response = requests.get(test_url, timeout=10)
        download_time = time.time() - start_time
        
        if download_time > 0:
            bandwidth_kbps = 1 / download_time
            logger.info(f"   估算带宽: {bandwidth_kbps:.1f} KB/s")
            
            if bandwidth_kbps < 100:
                logger.warning("⚠️ 网络带宽可能较低，影响Pinecone性能")
        
    except Exception as e:
        logger.error(f"   带宽测试失败: {str(e)}")

def analyze_pinecone_plan_limits():
    """分析Pinecone套餐限制"""
    logger.info("💳 Pinecone套餐和限制分析")
    
    try:
        from pinecone import Pinecone
        
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        pc = Pinecone(api_key=api_key)
        
        # 获取索引信息
        index = pc.Index("german-bge")
        
        logger.info("📊 当前索引配置:")
        
        # 尝试获取索引详情
        try:
            # 这个API可能需要不同的权限
            indexes = pc.list_indexes()
            for idx in indexes:
                if idx.name == "german-bge":
                    logger.info(f"   索引名: {idx.name}")
                    logger.info(f"   维度: {idx.dimension}")
                    logger.info(f"   度量: {idx.metric}")
                    logger.info(f"   Host: {idx.host}")
                    
                    # 分析host信息推断套餐
                    if "gcp-starter" in idx.host:
                        plan_type = "Starter (免费套餐)"
                        performance_limit = "较低性能限制"
                    elif "aws" in idx.host or "gcp" in idx.host:
                        plan_type = "Standard/Pro (付费套餐)"
                        performance_limit = "更高性能限制"
                    else:
                        plan_type = "未知套餐类型"
                        performance_limit = "未知性能限制"
                    
                    logger.info(f"   推断套餐: {plan_type}")
                    logger.info(f"   性能预期: {performance_limit}")
                    
        except Exception as e:
            logger.error(f"   获取索引详情失败: {str(e)}")
        
        # 分析不同套餐的理论性能
        logger.info("📈 不同套餐性能对比:")
        plans = [
            {
                "name": "Starter (免费)",
                "qps_limit": "5-10 QPS",
                "expected_performance": "10-20 向量/秒",
                "notes": "严格速率限制"
            },
            {
                "name": "Standard", 
                "qps_limit": "100+ QPS",
                "expected_performance": "50-100 向量/秒",
                "notes": "适中性能"
            },
            {
                "name": "Pro/Enterprise",
                "qps_limit": "1000+ QPS", 
                "expected_performance": "200+ 向量/秒",
                "notes": "高性能"
            }
        ]
        
        for plan in plans:
            logger.info(f"   {plan['name']}:")
            logger.info(f"     QPS限制: {plan['qps_limit']}")
            logger.info(f"     预期性能: {plan['expected_performance']}")
            logger.info(f"     说明: {plan['notes']}")
        
        logger.info("💡 性能优化建议:")
        logger.info("   1. 如果使用免费套餐，升级到付费套餐可显著提升性能")
        logger.info("   2. 批次大小优化：付费套餐可支持更大批次")
        logger.info("   3. 并发优化：付费套餐支持更高并发")
        
    except Exception as e:
        logger.error(f"❌ Pinecone套餐分析失败: {str(e)}")

def test_optimal_batch_sizes():
    """测试不同套餐下的最佳批次大小"""
    logger.info("🧪 批次大小优化测试")
    
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
        
        # 生成测试向量
        test_texts = [f"性能测试向量{i}" for i in range(20)]
        vectors = embedding_client.embed_batch(test_texts, batch_size=20)
        
        # 测试不同批次大小
        batch_sizes = [5, 10, 25, 50, 100]
        results = []
        
        for batch_size in batch_sizes:
            if batch_size > len(vectors):
                continue
                
            logger.info(f"🧪 测试批次大小: {batch_size}")
            
            # 准备测试向量
            test_vectors = []
            timestamp = int(time.time())
            
            for i in range(batch_size):
                test_vectors.append({
                    "id": f"batch_test_{timestamp}_{batch_size}_{i}",
                    "values": vectors[i % len(vectors)],
                    "metadata": {"batch_test": True, "batch_size": batch_size}
                })
            
            # 执行测试
            start_time = time.time()
            try:
                upsert_response = index.upsert(vectors=test_vectors)
                upsert_time = time.time() - start_time
                
                speed = batch_size / upsert_time if upsert_time > 0 else 0
                success = True
                error_msg = None
                
            except Exception as e:
                upsert_time = time.time() - start_time
                speed = 0
                success = False
                error_msg = str(e)
            
            result = {
                "batch_size": batch_size,
                "time": upsert_time,
                "speed": speed,
                "success": success,
                "error": error_msg
            }
            results.append(result)
            
            logger.info(f"   结果: {'成功' if success else '失败'}")
            logger.info(f"   耗时: {upsert_time:.2f}秒")
            logger.info(f"   速度: {speed:.1f} 向量/秒")
            
            if error_msg:
                logger.warning(f"   错误: {error_msg}")
            
            # 清理测试向量
            try:
                test_ids = [v["id"] for v in test_vectors]
                index.delete(ids=test_ids)
            except:
                pass
            
            time.sleep(1)  # 避免API限制
        
        # 分析结果
        logger.info("📊 批次大小性能总结:")
        logger.info("批次大小  |  耗时(秒)  |  速度(向量/秒)  |  状态")
        logger.info("-" * 50)
        
        for result in results:
            status = "✅ 成功" if result["success"] else "❌ 失败"
            logger.info(f"   {result['batch_size']:3d}    |   {result['time']:6.2f}   |      {result['speed']:6.1f}       | {status}")
        
        # 推荐最佳配置
        successful_results = [r for r in results if r["success"]]
        if successful_results:
            best_result = max(successful_results, key=lambda x: x["speed"])
            logger.info(f"🎯 当前配置下最佳批次大小: {best_result['batch_size']} (速度: {best_result['speed']:.1f} 向量/秒)")
        
    except Exception as e:
        logger.error(f"❌ 批次大小测试失败: {str(e)}")

def main():
    """主诊断函数"""
    logger.info("🔍 Pinecone性能诊断工具")
    logger.info("=" * 60)
    
    # 诊断1: 网络条件
    check_network_conditions()
    
    logger.info("-" * 40)
    
    # 诊断2: 套餐分析
    analyze_pinecone_plan_limits()
    
    logger.info("-" * 40)
    
    # 诊断3: 批次优化测试
    test_optimal_batch_sizes()
    
    logger.info("=" * 60)
    logger.info("🎯 性能优化建议总结:")
    logger.info("1. 检查并禁用网络代理（如果有）")
    logger.info("2. 确认Pinecone套餐等级和限制")
    logger.info("3. 根据测试结果调整批次大小")
    logger.info("4. 考虑增加分块大小到4000字符")

if __name__ == "__main__":
    main()
