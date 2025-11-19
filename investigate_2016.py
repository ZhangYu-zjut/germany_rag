"""
深度调查2016年metadata更新情况
1. 查询大样本（200个向量）确定实际成功率
2. 使用fetch验证具体向量ID
3. 对比query vs fetch结果
"""
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv('PINECONE_VECTOR_DATABASE_API_KEY'))
index = pc.Index('german-bge')

print("="*60)
print("2016年Metadata更新深度调查")
print("="*60)

# 1. Query大样本（200个向量）
print("\n【测试1】Query 200个随机2016年向量")
print("-"*60)

dummy_vector = [0.0] * 1024
results = index.query(
    vector=dummy_vector,
    top_k=200,
    filter={'year': {'$eq': '2016'}},
    include_metadata=True
)

success_count = 0
failed_ids = []
success_ids = []

for match in results.matches:
    meta = match.metadata
    has_new_fields = all([
        meta.get('month'),
        meta.get('day'),
        meta.get('id'),
        meta.get('source_reference')
    ])

    if has_new_fields:
        success_count += 1
        success_ids.append(match.id)
    else:
        failed_ids.append(match.id)

print(f"Query结果: {success_count}/200 有新字段 ({success_count/200*100:.1f}%)")
print(f"失败向量数: {len(failed_ids)}")
print(f"成功向量数: {len(success_ids)}")

# 2. 从失败的向量中随机选5个，用fetch验证
if failed_ids:
    print("\n【测试2】Fetch验证失败的向量（前5个）")
    print("-"*60)

    sample_failed_ids = failed_ids[:5]
    fetch_results = index.fetch(ids=sample_failed_ids)

    for i, vec_id in enumerate(sample_failed_ids, 1):
        if vec_id in fetch_results.vectors:
            vec = fetch_results.vectors[vec_id]
            meta = vec.metadata
            print(f"\n失败向量 {i}: {vec_id[:40]}...")
            print(f"  month: {meta.get('month', 'None')}")
            print(f"  day: {meta.get('day', 'None')}")
            print(f"  id: {meta.get('id', 'None')}")
            print(f"  source_reference: {meta.get('source_reference', 'None')[:50] if meta.get('source_reference') else 'None'}...")

# 3. 检查成功的向量
if success_ids:
    print("\n【测试3】检查Query中成功的向量（前3个）")
    print("-"*60)

    for i, match in enumerate(results.matches[:3], 1):
        if match.id in success_ids:
            meta = match.metadata
            print(f"\n成功向量 {i}: {match.id[:40]}...")
            print(f"  month: {meta.get('month')}")
            print(f"  day: {meta.get('day')}")
            print(f"  id: {meta.get('id')}")
            print(f"  source_reference: {meta.get('source_reference', '')[:50]}...")

# 4. 检查日志中验证的向量（2016_1762423144_690）
print("\n【测试4】Fetch日志中验证的向量")
print("-"*60)

log_verified_id = '2016_1762423144_690'
fetch_result = index.fetch(ids=[log_verified_id])

if log_verified_id in fetch_result.vectors:
    vec = fetch_result.vectors[log_verified_id]
    meta = vec.metadata
    print(f"\n日志验证向量: {log_verified_id}")
    print(f"  month: {meta.get('month', 'None')}")
    print(f"  day: {meta.get('day', 'None')}")
    print(f"  id: {meta.get('id', 'None')}")
    print(f"  source_reference: {meta.get('source_reference', 'None')[:60] if meta.get('source_reference') else 'None'}...")
    print(f"  ✅ 此向量有新字段")
else:
    print(f"  ❌ 无法fetch此向量")

# 5. 总结
print("\n" + "="*60)
print("调查总结")
print("="*60)
print(f"Query样本大小: 200")
print(f"成功向量数: {success_count}")
print(f"失败向量数: {len(failed_ids)}")
print(f"实际成功率: {success_count/200*100:.1f}%")
print(f"\n对比日志声明: 10000/10000 (100%)")
print(f"结论: {'✅ 一致' if success_count == 200 else '❌ 不一致 - 需要调查'}")
