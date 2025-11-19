"""
测试修复后的get_all_vectors_for_year方法 - 2016年
"""
import time
from update_pinecone_metadata_optimized import OptimizedMetadataUpdater

print("="*60)
print("测试修复后的向量获取方法 - 2016年")
print("="*60)
print()

# 创建更新器
updater = OptimizedMetadataUpdater(max_workers=20)

# 测试获取2016年所有向量
print("【测试1】使用修复后的list() API获取2016年所有向量")
print("-"*60)

start = time.time()
vectors = updater.get_all_vectors_for_year(2016)
elapsed = time.time() - start

print(f"\n获取结果:")
print(f"  获取向量数: {len(vectors)}")
print(f"  耗时: {elapsed:.1f}秒")
print(f"  平均速度: {len(vectors)/elapsed:.1f} 向量/秒")

if len(vectors) > 10000:
    print(f"\n✅ 成功！2016年实际有 {len(vectors)} 个向量 (超过10000限制)")
elif len(vectors) == 10000:
    print(f"\n⚠️ 警告！恰好10000个，可能还是被限制了")
else:
    print(f"\n✅ 2016年共 {len(vectors)} 个向量 (小于10000)")

print()
print("="*60)
print("结论")
print("="*60)
print(f"旧方法 (query top_k=10000): 只能获取10000个")
print(f"新方法 (list分页):获取到 {len(vectors)} 个")
print(f"差异: {len(vectors) - 10000} 个向量被遗漏")
