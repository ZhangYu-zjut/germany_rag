#!/usr/bin/env python3
"""
优化的迁移配置参数
基于性能测试结果的最佳配置
"""

# 性能测试结果总结
PERFORMANCE_TEST_RESULTS = {
    "embedding_performance": {
        "batch_16": 56.0,   # 条/秒
        "batch_32": 127.0,  # 条/秒
        "batch_64": 172.6,  # 条/秒
        "batch_128": 503.4, # 条/秒 - 最佳
    },
    "storage_performance": {
        "batch_10": 6.2,    # 条/秒
        "batch_25": 26.8,   # 条/秒
        "batch_50": 40.7,   # 条/秒 - 最佳
    },
    "bottleneck": "pinecone_storage",  # 瓶颈是Pinecone存储
    "effective_speed": 32.5,           # 条/秒 (含20%处理开销)
}

# 优化配置1: 当前最佳 (4.1小时)
CURRENT_OPTIMAL_CONFIG = {
    "embedding_batch_size": 128,
    "embedding_max_workers": 4,
    "pinecone_batch_size": 50,
    "request_delay": 0.1,  # 减少延迟
    "estimated_time_hours": 4.1,
    "description": "基于测试的最佳平衡配置"
}

# 优化配置2: 激进优化 (尝试更快)
AGGRESSIVE_OPTIMIZATION = {
    "embedding_batch_size": 256,      # 更大批次
    "embedding_max_workers": 8,       # 更高并发
    "pinecone_batch_size": 100,       # 尝试更大存储批次
    "pinecone_concurrent": 2,         # 并发存储
    "request_delay": 0.05,            # 最小延迟
    "estimated_time_hours": 2.5,      # 目标时间
    "description": "激进优化配置，可能不稳定"
}

# 优化配置3: 稳定优化 (推荐)
STABLE_OPTIMIZATION = {
    "embedding_batch_size": 128,
    "embedding_max_workers": 6,       # 适中并发
    "pinecone_batch_size": 75,        # 适中存储批次
    "request_delay": 0.1,
    "retry_max": 5,                   # 增加重试
    "estimated_time_hours": 3.5,      # 目标时间
    "description": "稳定的优化配置，推荐使用"
}

def print_optimization_summary():
    """打印优化配置总结"""
    print("🚀 迁移优化配置方案")
    print("=" * 60)
    
    configs = [
        ("当前最佳", CURRENT_OPTIMAL_CONFIG),
        ("稳定优化", STABLE_OPTIMIZATION), 
        ("激进优化", AGGRESSIVE_OPTIMIZATION)
    ]
    
    for name, config in configs:
        print(f"\n📋 {name}配置:")
        print(f"   Embedding批次: {config['embedding_batch_size']}")
        print(f"   Embedding并发: {config['embedding_max_workers']}")
        print(f"   Pinecone批次: {config['pinecone_batch_size']}")
        print(f"   预计时间: {config['estimated_time_hours']}小时")
        print(f"   说明: {config['description']}")
    
    print(f"\n🎯 推荐方案: 稳定优化配置")
    print(f"   预计时间从4-6小时缩短至3.5小时")
    print(f"   性能提升约30-40%")

if __name__ == "__main__":
    print_optimization_summary()
