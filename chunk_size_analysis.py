#!/usr/bin/env python3
"""
分析分块大小对迁移效率的影响
对比不同chunk_size的性能差异
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

def analyze_chunk_size_impact():
    """分析分块大小对迁移效率的影响"""
    print("📊 分块大小对迁移效率的影响分析")
    print("=" * 60)
    
    # 假设场景：2015年数据分析
    original_data_size = 50_000_000  # 50MB原始文本
    
    chunk_scenarios = [
        {
            "chunk_size": 1000,
            "overlap": 100,
            "description": "当前配置",
        },
        {
            "chunk_size": 2000, 
            "overlap": 200,
            "description": "中等块大小",
        },
        {
            "chunk_size": 4000,
            "overlap": 400, 
            "description": "大块大小（用户建议）",
        },
        {
            "chunk_size": 8000,
            "overlap": 800,
            "description": "极大块大小",
        }
    ]
    
    print("🔍 不同分块策略对比:")
    print("块大小  |  预估块数  |  传输次数  |  embedding时间  |  存储时间  |  总时间  |  优缺点")
    print("-" * 100)
    
    for scenario in chunk_scenarios:
        chunk_size = scenario["chunk_size"]
        overlap = scenario["overlap"]
        
        # 估算块数量 (考虑重叠)
        effective_chunk_size = chunk_size - overlap
        estimated_chunks = original_data_size // effective_chunk_size
        
        # 估算传输时间 (基于实际测试数据)
        embedding_time_per_chunk = 1 / 503.4  # 秒/chunk (基于128批次)
        storage_time_per_chunk = 1 / 40.7     # 秒/chunk (基于50批次)
        
        total_embedding_time = estimated_chunks * embedding_time_per_chunk
        total_storage_time = estimated_chunks * storage_time_per_chunk
        total_time = total_embedding_time + total_storage_time
        
        # 传输次数估算 (基于批次)
        embedding_batches = estimated_chunks // 128 + (1 if estimated_chunks % 128 else 0)
        storage_batches = estimated_chunks // 50 + (1 if estimated_chunks % 50 else 0)
        total_api_calls = embedding_batches + storage_batches
        
        # 优缺点分析
        if chunk_size <= 1000:
            pros_cons = "细粒度，精确检索，但块数多"
        elif chunk_size <= 2000:
            pros_cons = "平衡性能和精度"
        elif chunk_size <= 4000:
            pros_cons = "减少传输，但可能影响检索精度"
        else:
            pros_cons = "最少传输，但检索精度大幅下降"
        
        print(f" {chunk_size:4d}   |  {estimated_chunks:8,d}  |   {total_api_calls:6d}   |    {total_embedding_time:8.1f}s   |   {total_storage_time:7.1f}s   | {total_time:6.1f}s | {pros_cons}")
    
    print("\n💡 分块大小优化分析:")
    print("1. 📉 减少块数量：4000字符确实能减少传输次数约75%")
    print("2. ⚡ 性能提升：总处理时间可减少约75%") 
    print("3. ⚠️  检索精度风险：大块可能影响语义检索准确性")
    print("4. 🧠 内存影响：更大的块需要更多embedding内存")
    
    print("\n🎯 建议:")
    print("- 📊 当前1000字符：适合精确检索，但传输量大")
    print("- 🚀 4000字符优化：显著减少传输时间，推荐尝试")
    print("- ⚖️  平衡方案：2000-3000字符可能是最佳平衡点")
    
def calculate_memory_impact():
    """计算不同分块大小对内存的影响"""
    print("\n🧠 内存影响分析:")
    print("=" * 40)
    
    chunk_sizes = [1000, 2000, 4000, 8000]
    batch_size = 128
    
    for chunk_size in chunk_sizes:
        # 估算内存使用 (粗略计算)
        # 每个字符约1-2字节，embedding向量1024维*4字节
        text_memory_mb = (chunk_size * batch_size * 2) / (1024*1024)  # 文本内存
        vector_memory_mb = (1024 * 4 * batch_size) / (1024*1024)      # 向量内存
        total_memory_mb = text_memory_mb + vector_memory_mb
        
        print(f"块大小{chunk_size:4d}: 文本{text_memory_mb:5.1f}MB + 向量{vector_memory_mb:5.1f}MB = 总计{total_memory_mb:5.1f}MB")
    
    print("\n📊 内存结论:")
    print("- GPU显存16GB足够处理任何合理的分块大小") 
    print("- 4000字符分块不会造成内存问题")
    print("- 主要限制是网络传输，不是内存")

if __name__ == "__main__":
    analyze_chunk_size_impact()
    calculate_memory_impact()
