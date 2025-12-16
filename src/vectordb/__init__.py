"""
向量数据库模块初始化

【云端部署优化】使用懒加载，避免在不需要时导入pymilvus
"""

# 懒加载：只在实际使用时才导入
def __getattr__(name):
    if name == "MilvusClient":
        from .client import MilvusClient
        return MilvusClient
    elif name == "MilvusCollectionManager":
        from .collection import MilvusCollectionManager
        return MilvusCollectionManager
    elif name == "MilvusRetriever":
        from .retriever import MilvusRetriever
        return MilvusRetriever
    elif name == "PineconeRetriever":
        from .pinecone_retriever import PineconeRetriever
        return PineconeRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "MilvusClient",
    "MilvusCollectionManager",
    "MilvusRetriever",
    "PineconeRetriever"
]
