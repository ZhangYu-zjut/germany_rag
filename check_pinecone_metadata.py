"""检查Pinecone中存储的metadata是否有None值"""

from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()
pc = Pinecone(api_key=os.getenv('PINECONE_VECTOR_DATABASE_API_KEY'))
index = pc.Index('german-bge')

# 查询2017年的数据
result = index.query(
    vector=[0.0] * 1024,
    top_k=5,
    filter={'year': {'$eq': '2017'}},
    include_metadata=True
)

print('=== Pinecone中2017年数据的metadata ===\n')
for i, match in enumerate(result.matches, 1):
    meta = match.metadata
    print(f'文档 {i} (ID: {match.id[:20]}...):')
    print(f'  year: {repr(meta.get("year"))} (type: {type(meta.get("year")).__name__})')
    print(f'  month: {repr(meta.get("month"))} (type: {type(meta.get("month")).__name__})')
    print(f'  day: {repr(meta.get("day"))} (type: {type(meta.get("day")).__name__})')
    print(f'  session: {repr(meta.get("session"))} (type: {type(meta.get("session")).__name__})')
    print(f'  speaker: {meta.get("speaker", "N/A")[:40]}')

    if meta.get("month") is None or meta.get("day") is None:
        print(f'  ⚠️ 发现None值！')
    print()
