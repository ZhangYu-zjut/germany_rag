#!/usr/bin/env python3
"""
检查目标文档是否在Pinecone中
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from src.vectordb.pinecone_retriever import PineconeRetriever
from src.llm.embeddings import GeminiEmbeddingClient

def main():
    # 创建检索器
    print("🔍 连接Pinecone...")
    retriever = PineconeRetriever(
        index_name="german-bge"
    )

    # 直接通过ID查询文档
    target_id = "2017_1762423575_2922"
    print(f"\n📝 检查目标文档: {target_id}")

    try:
        result = retriever.index.fetch(ids=[target_id])
        if result.vectors:
            print(f"✅ 文档 {target_id} 存在于Pinecone中！")
            vec = result.vectors[target_id]
            text = vec.metadata.get('text', '')

            print(f"\n" + "=" * 80)
            print(f"📄 文档完整内容:")
            print("=" * 80)
            print(text)

            print(f"\n" + "=" * 80)
            print(f"🔍 关键短语检查:")
            print("=" * 80)

            if "Zwang durchsetzen" in text:
                print(f"   ✅ 'Zwang durchsetzen' 存在")
                start_idx = text.find("Zwang durchsetzen")
                context = text[max(0, start_idx-150):start_idx+200]
                print(f"\n   上下文: ...{context}...")
            else:
                print(f"   ❌ 'Zwang durchsetzen' 不存在")

            print(f"\n" + "=" * 80)
            print(f"📊 元数据:")
            print("=" * 80)
            print(f"   年份: {vec.metadata.get('year', 'N/A')}")
            print(f"   发言人: {vec.metadata.get('speaker', 'N/A')}")
            print(f"   党派: {vec.metadata.get('group', 'N/A')}")
            print(f"   日期: {vec.metadata.get('year', 'N/A')}-{vec.metadata.get('month', 'N/A')}-{vec.metadata.get('day', 'N/A')}")
        else:
            print(f"❌ 文档 {target_id} 不存在于Pinecone中！")
            print(f"\n⚠️ 可能的原因:")
            print(f"   1. 数据迁移时此文档未被迁移")
            print(f"   2. 文档ID格式不匹配")
            print(f"   3. 数据源中不存在此文档")
    except Exception as e:
        print(f"⚠️ 查询失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
