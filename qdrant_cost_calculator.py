#!/usr/bin/env python3
"""
Qdrant Cloud 成本精确计算器
"""

print('📊 Qdrant Cloud 成本重新计算')
print('=' * 40)

# 实际数据需求
vectors = 2_089_222  # 向量数量
dimensions = 1024    # 向量维度
bytes_per_float = 4  # float32

# 存储需求计算
vector_storage_bytes = vectors * dimensions * bytes_per_float
vector_storage_gb = vector_storage_bytes / (1024 ** 3)

# 元数据存储估算 (每个向量约200字节元数据)
metadata_bytes = vectors * 200
metadata_gb = metadata_bytes / (1024 ** 3)

total_storage_gb = vector_storage_gb + metadata_gb

print(f'向量存储需求: {vector_storage_gb:.2f} GB')
print(f'元数据存储需求: {metadata_gb:.2f} GB')
print(f'总存储需求: {total_storage_gb:.2f} GB')
print()

print('Qdrant Cloud 定价模式分析:')
print('=' * 40)

# Qdrant Cloud 一般定价结构
print('🔍 基于行业标准的估算:')
print('  • 最小集群 (1GB RAM, 0.5 vCPU): ~$25-35/月')
print('  • 存储费用: ~$0.10-0.15/GB/月')
print(f'  • 我们的存储成本: ~${total_storage_gb * 0.10:.2f}-{total_storage_gb * 0.15:.2f}/月')
print()

min_cluster_cost = 25
max_cluster_cost = 35
storage_cost_min = total_storage_gb * 0.10
storage_cost_max = total_storage_gb * 0.15

total_min = min_cluster_cost + storage_cost_min
total_max = max_cluster_cost + storage_cost_max

print(f'📈 预估月费用:')
print(f'  • 最低: ${total_min:.2f}/月')
print(f'  • 最高: ${total_max:.2f}/月')
print(f'  • 平均: ${(total_min + total_max)/2:.2f}/月')
print()

print('🎯 修正后的方案1成本:')
print('=' * 40)
print('DeepInfra Embedding + Qdrant Cloud:')
print(f'  • Embedding (一次性): ~$2-3')
print(f'  • Qdrant Cloud (月费): ${total_min:.2f}-{total_max:.2f}')
print(f'  • 首月总计: ${2 + total_min:.2f}-{3 + total_max:.2f}')
print(f'  • 后续月费: ${total_min:.2f}-{total_max:.2f}')
print()

print('⚠️  重要提醒:')
print('=' * 40)
print('• Qdrant Cloud 提供免费试用')
print('• 建议先创建小集群测试')
print('• 可根据实际使用情况调整配置')
print('• 存储费用可能根据地区和配置有所不同')
print()

print('🚀 立即验证步骤:')
print('1. 访问 https://cloud.qdrant.tech')
print('2. 注册并创建最小配置集群')
print('3. 查看实际定价确认')
print('4. 开始免费试用测试')
