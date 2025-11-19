"""检查2016年实际向量数量"""
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv('PINECONE_VECTOR_DATABASE_API_KEY'))
index = pc.Index('german-bge')

print("="*60)
print("检查2016年实际向量数量")
print("="*60)

# 查询top_k=10000
dummy_vector = [0.0] * 1024
results = index.query(
    vector=dummy_vector,
    top_k=10000,
    filter={'year': {'$eq': '2016'}},
    include_metadata=True
)

print(f"\nQuery (top_k=10000): {len(results.matches)} 个向量")

if len(results.matches) == 10000:
    print("⚠️ 返回了正好10000个，说明可能有更多！")

    print(f"\n前10个向量ID:")
    for i, match in enumerate(results.matches[:10]):
        print(f"  {i+1}. {match.id}")

    print(f"\n中间10个向量ID (4995-5005):")
    for i, match in enumerate(results.matches[4995:5005]):
        print(f"  {4996+i}. {match.id}")

    print(f"\n后10个向量ID:")
    for i, match in enumerate(results.matches[-10:]):
        print(f"  {9991+i}. {match.id}")

print("\n" + "="*60)
print("结论")
print("="*60)
print("Pinecone的query方法有top_k=10000限制")
print("无法通过单次query获取超过10000个的向量")
print("需要使用list()或分页方法来获取所有向量")
