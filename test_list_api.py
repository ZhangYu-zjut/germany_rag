"""测试Pinecone list() API的返回格式"""
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv('PINECONE_VECTOR_DATABASE_API_KEY'))
index = pc.Index('german-bge')

print("测试list() API返回格式")
print("="*60)

# 测试list()调用
result = index.list(prefix='2016_', limit=5)

print(f"result类型: {type(result)}")
print(f"result内容: {result}")
print(f"\n可用的属性/方法:")
print([attr for attr in dir(result) if not attr.startswith('_')])

# 尝试迭代
print(f"\n尝试迭代结果:")
count = 0
for item in result:
    count += 1
    print(f"  项{count}: {item} (类型: {type(item)})")
    if hasattr(item, 'id'):
        print(f"    ID: {item.id}")
    if count >= 3:
        break

print(f"\n总共迭代了 {count} 个项")
