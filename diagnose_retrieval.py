#!/usr/bin/env python3
"""
诊断关键文档未被召回的根本原因
"""
import sys
sys.path.append('.')

from pinecone import Pinecone
from src.config import settings
from src.llm.embeddings import GeminiEmbeddingClient
import json

# 关键文档信息
TARGET_TEXT_ID = "2017_1762423575_2922"
TARGET_PHRASE = "Zwang durchsetzen"
QUERY = "Wie haben sich die Positionen der CDU/CSU zur Migrationspolitik zwischen 2017 und 2019 im Vergleich verändert?"

print("=" * 80)
print("🔍 检索失败诊断：为什么'Zwang durchsetzen'未被召回？")
print("=" * 80)
print()

# 1. 检查文档是否在Pinecone中
print("【步骤1】检查目标文档是否在Pinecone索引中")
print(f"  目标text_id: {TARGET_TEXT_ID}")
print()

pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)

try:
    # 尝试直接fetch
    result = index.fetch(ids=[TARGET_TEXT_ID])
    
    if TARGET_TEXT_ID in result.get('vectors', {}):
        print("  ✅ 文档存在于Pinecone中！")
        doc_metadata = result['vectors'][TARGET_TEXT_ID].get('metadata', {})
        print(f"  📄 元数据: {json.dumps(doc_metadata, ensure_ascii=False, indent=2)}")
        print()
        
        # 检查文本内容
        doc_text = doc_metadata.get('text', '')
        if TARGET_PHRASE in doc_text:
            print(f"  ✅ 确认包含关键短语: '{TARGET_PHRASE}'")
        else:
            print(f"  ❌ 文档不包含'{TARGET_PHRASE}'（可能text_id有误）")
        print()
        
    else:
        print(f"  ❌ 文档不存在！可能原因：")
        print(f"     1. 数据迁移时该文档未被索引")
        print(f"     2. text_id格式错误")
        print(f"  → 这是数据问题，不是检索算法问题！")
        exit(1)
        
except Exception as e:
    print(f"  ❌ Fetch失败: {e}")
    exit(1)

# 2. 计算查询与目标文档的向量相似度
print("【步骤2】计算查询与目标文档的向量相似度")
print(f"  查询: {QUERY}")
print()

embed_client = GeminiEmbeddingClient()
query_vector = embed_client.embed_batch([QUERY])[0]

# 获取目标文档的向量
doc_vector = result['vectors'][TARGET_TEXT_ID]['values']

# 计算余弦相似度
import numpy as np
similarity = np.dot(query_vector, doc_vector) / (
    np.linalg.norm(query_vector) * np.linalg.norm(doc_vector)
)

print(f"  📊 相似度: {similarity:.4f}")
print()

if similarity < 0.5:
    print(f"  ❌ 相似度过低（<0.5）！这是向量检索的根本问题！")
    print(f"  → 证据：查询的语义与文档差距大")
    print(f"  → 方案：需要Query扩展或BM25关键词检索")
elif similarity < 0.7:
    print(f"  ⚠️  相似度偏低（0.5-0.7）")
    print(f"  → 可能在top-50边缘，需要验证实际检索结果")
else:
    print(f"  ✅ 相似度较高（>0.7）")
    print(f"  → 如果仍未召回，可能是元数据过滤或top_k不足的问题")

print()

# 3. 模拟实际检索（不带元数据过滤）
print("【步骤3】模拟实际检索（无元数据过滤）")
results_no_filter = index.query(
    vector=query_vector,
    top_k=100,
    include_metadata=True
)

# 检查目标文档在哪个位置
target_rank = None
for rank, match in enumerate(results_no_filter['matches'], start=1):
    if match['id'] == TARGET_TEXT_ID:
        target_rank = rank
        print(f"  ✅ 目标文档在无过滤检索中排名: 第{rank}位（相似度: {match['score']:.4f}）")
        break

if target_rank is None:
    print(f"  ❌ 目标文档不在top-100中！")
    print(f"  → 证据：向量相似度确实太低")
    print(f"  → 方案：必须使用BM25或Query扩展")
elif target_rank > 50:
    print(f"  ⚠️  目标文档在第{target_rank}位，超出top-50")
    print(f"  → 可能原因：top_k=50不足，或ReRank前就被截断")
    print(f"  → 方案：增加top_k或优化相似度")
else:
    print(f"  ✅ 目标文档在top-50内")
    print(f"  → 问题可能在元数据过滤或ReRank阶段")

print()

# 4. 模拟带元数据过滤的检索（年份过滤）
print("【步骤4】模拟带元数据过滤的检索（year=2017）")
results_with_filter = index.query(
    vector=query_vector,
    top_k=50,
    filter={"year": "2017"},
    include_metadata=True
)

target_rank_filtered = None
for rank, match in enumerate(results_with_filter['matches'], start=1):
    if match['id'] == TARGET_TEXT_ID:
        target_rank_filtered = rank
        print(f"  ✅ 目标文档在过滤检索中排名: 第{rank}位（相似度: {match['score']:.4f}）")
        break

if target_rank_filtered is None:
    print(f"  ❌ 目标文档不在year=2017的top-50中！")
    if target_rank and target_rank <= 100:
        print(f"  → 原因：在全局检索中排名第{target_rank}，但2017年内排名不够高")
        print(f"  → 说明：2017年有更相关的文档，导致此文档被挤出top-50")
    else:
        print(f"  → 原因：相似度太低，即使限定年份也无法召回")
    print(f"  → 方案：Query扩展（生成更具体的查询）或BM25（精确匹配'Zwang'）")

print()

# 5. 关键词匹配测试
print("【步骤5】关键词匹配测试（如果有BM25会怎样）")
print(f"  查询关键词: {QUERY.split()}")
print(f"  目标文档关键词: Zwang durchsetzen Ausreisepflicht")
print()

if "Zwang" in QUERY or "durchsetzen" in QUERY:
    print(f"  ✅ 查询包含精确关键词，BM25会直接召回")
else:
    print(f"  ❌ 查询不包含'Zwang'或'durchsetzen'")
    print(f"  → 但Query扩展可能生成包含这些词的查询：")
    print(f"     'CDU/CSU Abschiebung Zwang 2017'")
    print(f"     'Union Ausreisepflicht durchsetzen 2017'")
    print(f"  → BM25会通过扩展查询召回目标文档")

print()
print("=" * 80)
print("📊 诊断总结")
print("=" * 80)
print()

# 生成诊断报告
if similarity < 0.5:
    print("【根本原因】向量相似度过低（<0.5）")
    print()
    print("【证据链】")
    print(f"  1. 目标文档存在于Pinecone ✓")
    print(f"  2. 查询向量相似度: {similarity:.4f} (太低)")
    print(f"  3. 无过滤检索排名: 第{target_rank or '>100'}位")
    print(f"  4. 有过滤检索排名: 未进入top-50")
    print()
    print("【推荐方案】")
    print("  🎯 Query扩展 (优先级1):")
    print("     - 生成包含'Zwang', 'Abschiebung', 'durchsetzen'的查询")
    print("     - 预期相似度提升到0.6+")
    print()
    print("  🎯 BM25混合检索 (优先级2):")
    print("     - 精确匹配'Zwang durchsetzen'")
    print("     - 与向量检索融合，互补优势")
    print()
    print("【方案依据】")
    print("  ✅ 数据依据：实测相似度过低")
    print("  ✅ 理论依据：语义gap需要关键词匹配弥补")
    
elif target_rank and target_rank > 50:
    print("【根本原因】top_k不足或竞争文档过多")
    print()
    print("【证据链】")
    print(f"  1. 目标文档存在 ✓")
    print(f"  2. 查询向量相似度: {similarity:.4f} (可接受)")
    print(f"  3. 无过滤检索排名: 第{target_rank}位 (超出top-50)")
    print()
    print("【推荐方案】")
    print("  🎯 增加top_k到100 (优先级1)")
    print("  🎯 Query扩展 (优先级2)")

else:
    print("【疑似原因】ReRank过度过滤或其他环节问题")
    print("  → 需要进一步分析ReRank日志")

