"""
快速检查哪些年份受top_k=10000限制影响
只使用query()检查，不使用慢速的list()
"""
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv('PINECONE_VECTOR_DATABASE_API_KEY'))
index = pc.Index('german-bge')

print("="*70)
print("快速检查所有年份 - 识别受top_k=10000限制影响的年份")
print("="*70)
print()

years = range(2015, 2025)  # 2015-2024
affected_years = []
safe_years = []
dummy_vector = [0.0] * 1024

for year in years:
    print(f"检查 {year} 年...", end=" ")

    # 使用query查询（受10000限制）
    results = index.query(
        vector=dummy_vector,
        top_k=10000,
        filter={'year': {'$eq': str(year)}},
        include_metadata=False  # 不需要metadata，更快
    )

    count = len(results.matches)

    if count == 10000:
        print(f"⚠️ 返回10000个 (可能受影响)")
        affected_years.append(year)
    else:
        print(f"✅ {count:,} 个向量 (安全)")
        safe_years.append((year, count))

print()
print("="*70)
print("总结")
print("="*70)
print()

if safe_years:
    print(f"✅ 安全的年份（向量数 < 10000）:")
    for year, count in safe_years:
        print(f"   {year}: {count:,} 个向量")

print()

if affected_years:
    print(f"⚠️ 可能受影响的年份（返回正好10000个）:")
    for year in affected_years:
        print(f"   {year}: 可能实际 > 10000个向量")
else:
    print("✅ 所有年份都安全，无年份受影响")

print()
print("="*70)
print("建议")
print("="*70)
print()

if affected_years:
    print(f"需要使用修复后的脚本重新更新以下年份:")
    for year in affected_years:
        print(f"  - {year}")
    print()
    print("原因: 这些年份实际向量数 > 10000，旧脚本只更新了前10000个")
else:
    print("✅ 所有年份都在10000个以内，之前的更新应该是完整的")

print()
print("="*70)
