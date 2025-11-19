#!/usr/bin/env python3
"""
检查Pinecone连接和german-bge index状态
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
load_dotenv()

def check_pinecone_connection():
    """检查Pinecone连接状态"""
    print("🔍 检查Pinecone配置...")

    # 检查环境变量
    api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
    host = os.getenv("PINECONE_HOST")

    if not api_key:
        print("❌ PINECONE_VECTOR_DATABASE_API_KEY 未设置")
        return False

    if not host:
        print("❌ PINECONE_HOST 未设置")
        return False

    print(f"✅ API Key: {api_key[:10]}...")
    print(f"✅ Host: {host}")

    # 尝试连接Pinecone
    try:
        from pinecone import Pinecone

        print("\n🔗 连接Pinecone...")
        pc = Pinecone(api_key=api_key)

        # 列出所有indexes
        print("\n📋 列出所有indexes:")
        indexes = pc.list_indexes()

        for idx in indexes:
            print(f"  - {idx.name}: {idx.dimension}维, {idx.metric}")

        # 检查german-bge index
        print("\n🎯 检查german-bge index:")
        index_names = [idx.name for idx in indexes]

        if "german-bge" in index_names:
            print("✅ german-bge index存在")

            # 连接到index
            index = pc.Index("german-bge", host=host)

            # 获取统计信息
            stats = index.describe_index_stats()
            print(f"\n📊 Index统计信息:")
            print(f"  - 维度: {stats.get('dimension', 'N/A')}")
            print(f"  - 总向量数: {stats.get('total_vector_count', 0)}")
            print(f"  - Namespaces: {stats.get('namespaces', {})}")

            return True
        else:
            print("❌ german-bge index不存在")
            print("💡 可用的indexes:", index_names)
            return False

    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_pinecone_connection()

    if success:
        print("\n✅ Pinecone连接检查成功!")
    else:
        print("\n❌ Pinecone连接检查失败")
