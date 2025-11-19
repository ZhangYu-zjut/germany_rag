"""
检查所有年份的实际向量数量
找出哪些年份超过10000个向量（受到top_k=10000限制的影响）
"""
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv('PINECONE_VECTOR_DATABASE_API_KEY'))
index = pc.Index('german-bge')

print("="*70)
print("检查所有年份的实际向量数量")
print("="*70)
print()

years = range(2015, 2025)  # 2015-2024
affected_years = []
safe_years = []

for year in years:
    print(f"检查 {year} 年...")

    # 使用query查询（受10000限制）
    dummy_vector = [0.0] * 1024
    results = index.query(
        vector=dummy_vector,
        top_k=10000,
        filter={'year': {'$eq': str(year)}},
        include_metadata=True
    )

    count = len(results.matches)

    if count == 10000:
        status = "⚠️ 可能超过10000（受影响）"
        affected_years.append(year)
    else:
        status = f"✅ {count} 个向量（安全）"
        safe_years.append((year, count))

    print(f"  {year}: {status}")
    print()

print("="*70)
print("总结")
print("="*70)
print()

print(f"✅ 安全的年份（向量数 < 10000）:")
for year, count in safe_years:
    print(f"   {year}: {count:,} 个向量")

print()
print(f"⚠️ 可能受影响的年份（返回正好10000个）:")
for year in affected_years:
    print(f"   {year}: 可能超过10000个向量")

print()
print(f"总计:")
print(f"  安全年份: {len(safe_years)} 个")
print(f"  受影响年份: {len(affected_years)} 个")

print()
print("="*70)
print("建议")
print("="*70)
print()
if affected_years:
    print(f"需要使用修复后的脚本重新更新以下年份:")
    for year in affected_years:
        print(f"  - {year}")
else:
    print("✅ 所有年份都安全，无需重新更新")
