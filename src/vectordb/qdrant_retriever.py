"""
Qdrant检索器实现
提供高级检索功能，支持向量搜索和元数据过滤
"""

from typing import List, Dict, Any, Optional, Union
import time

from ..utils.logger import logger
from .qdrant_client import QdrantClient


class QdrantRetriever:
    """
    Qdrant检索器
    提供德国议会数据的高级检索功能
    """
    
    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection_name: str = "german_parliament",
        default_limit: int = 10
    ):
        """
        初始化Qdrant检索器
        
        Args:
            qdrant_client: Qdrant客户端实例
            collection_name: 集合名称
            default_limit: 默认返回结果数量
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        self.default_limit = default_limit
        
        logger.info(
            f"[QdrantRetriever] 初始化检索器，集合: {collection_name}, "
            f"默认限制: {default_limit}"
        )
        
        # 验证集合存在（如果不存在，记录警告但不抛出异常）
        if not self._verify_collection():
            logger.warning(f"[QdrantRetriever] 集合 {collection_name} 不存在，将在数据导入时创建")
    
    def _verify_collection(self) -> bool:
        """验证集合是否存在且可访问"""
        try:
            info = self.client.get_collection_info(self.collection_name)
            logger.info(
                f"[QdrantRetriever] 集合验证成功: {info['name']}, "
                f"数据点: {info['points_count']}"
            )
            return True
        except Exception as e:
            logger.error(f"[QdrantRetriever] 集合验证失败: {str(e)}")
            return False
    
    def search(
        self,
        query_vector: List[float],
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        基础向量搜索
        
        Args:
            query_vector: 查询向量
            limit: 返回结果数量
            score_threshold: 分数阈值
            filters: 元数据过滤条件
            
        Returns:
            List[Dict]: 搜索结果
        """
        if limit is None:
            limit = self.default_limit
        
        start_time = time.time()
        
        try:
            # 解析过滤条件
            year_filter = filters.get("year") if filters else None
            party_filter = filters.get("party") if filters else None
            speaker_filter = filters.get("speaker") if filters else None
            topic_filter = filters.get("topic") if filters else None
            
            # 执行搜索
            results = self.client.search_german_parliament(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                year_filter=year_filter,
                party_filter=party_filter,
                speaker_filter=speaker_filter,
                topic_filter=topic_filter,
                score_threshold=score_threshold
            )
            
            search_time = time.time() - start_time
            logger.info(
                f"[QdrantRetriever] 搜索完成，返回 {len(results)} 个结果，"
                f"耗时 {search_time:.3f}s"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[QdrantRetriever] 搜索失败: {str(e)}")
            raise
    
    def search_by_year_range(
        self,
        query_vector: List[float],
        start_year: int,
        end_year: int,
        limit: Optional[int] = None,
        party_filter: Optional[Union[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        按年份范围搜索
        
        Args:
            query_vector: 查询向量
            start_year: 起始年份
            end_year: 结束年份
            limit: 返回结果数量
            party_filter: 党派过滤
            
        Returns:
            List[Dict]: 搜索结果
        """
        if limit is None:
            limit = self.default_limit
        
        logger.info(
            f"[QdrantRetriever] 按年份范围搜索: {start_year}-{end_year}"
        )
        
        # 简化实现：使用start_year作为年份过滤
        # TODO: 实现真正的范围查询
        filters = {"year": start_year}
        if party_filter:
            filters["party"] = party_filter
        
        return self.search(
            query_vector=query_vector,
            limit=limit,
            filters=filters
        )
    
    def search_by_party(
        self,
        query_vector: List[float],
        parties: Union[str, List[str]],
        limit: Optional[int] = None,
        year_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        按党派搜索
        
        Args:
            query_vector: 查询向量
            parties: 党派名称(单个或列表)
            limit: 返回结果数量
            year_filter: 年份过滤
            
        Returns:
            List[Dict]: 搜索结果
        """
        if limit is None:
            limit = self.default_limit
        
        if isinstance(parties, str):
            parties = [parties]
        
        logger.info(f"[QdrantRetriever] 按党派搜索: {parties}")
        
        filters = {"party": parties[0] if len(parties) == 1 else parties}
        if year_filter:
            filters["year"] = year_filter
        
        return self.search(
            query_vector=query_vector,
            limit=limit,
            filters=filters
        )
    
    def search_by_speaker(
        self,
        query_vector: List[float],
        speaker: str,
        limit: Optional[int] = None,
        year_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        按演讲者搜索
        
        Args:
            query_vector: 查询向量
            speaker: 演讲者姓名
            limit: 返回结果数量
            year_filter: 年份过滤
            
        Returns:
            List[Dict]: 搜索结果
        """
        if limit is None:
            limit = self.default_limit
        
        logger.info(f"[QdrantRetriever] 按演讲者搜索: {speaker}")
        
        filters = {"speaker": speaker}
        if year_filter:
            filters["year"] = year_filter
        
        return self.search(
            query_vector=query_vector,
            limit=limit,
            filters=filters
        )
    
    def hybrid_search(
        self,
        query_vector: List[float],
        text_query: str,
        limit: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        vector_weight: float = 0.7,
        text_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        混合搜索 (向量 + 文本)
        
        注意：当前版本主要使用向量搜索，文本权重用于后处理
        
        Args:
            query_vector: 查询向量
            text_query: 文本查询
            limit: 返回结果数量
            metadata_filter: 元数据过滤
            vector_weight: 向量搜索权重
            text_weight: 文本搜索权重
            
        Returns:
            List[Dict]: 搜索结果
        """
        if limit is None:
            limit = self.default_limit
        
        logger.info(f"[QdrantRetriever] 混合搜索: 向量权重={vector_weight}, 文本权重={text_weight}")
        
        # 执行向量搜索
        vector_results = self.search(
            query_vector=query_vector,
            limit=limit * 2,  # 获取更多结果用于重排
            filters=metadata_filter
        )
        
        # 简单的文本匹配后处理
        if text_query and text_weight > 0:
            text_query_lower = text_query.lower()
            
            for result in vector_results:
                text = result.get("text", "").lower()
                
                # 简单的文本匹配分数
                text_score = 0.0
                if text_query_lower in text:
                    text_score = 1.0
                elif any(word in text for word in text_query_lower.split()):
                    text_score = 0.5
                
                # 组合分数
                original_score = result["score"]
                combined_score = (
                    original_score * vector_weight + 
                    text_score * text_weight
                )
                result["combined_score"] = combined_score
                result["text_score"] = text_score
            
            # 按组合分数重排
            vector_results.sort(key=lambda x: x.get("combined_score", x["score"]), reverse=True)
        
        # 返回指定数量的结果
        final_results = vector_results[:limit]
        
        logger.info(
            f"[QdrantRetriever] 混合搜索完成，返回 {len(final_results)} 个结果"
        )
        
        return final_results
    
    def get_similar_documents(
        self,
        document_id: Union[str, int],
        limit: Optional[int] = None,
        exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取与指定文档相似的文档
        
        Args:
            document_id: 文档ID
            limit: 返回结果数量
            exclude_self: 是否排除自身
            
        Returns:
            List[Dict]: 相似文档列表
        """
        if limit is None:
            limit = self.default_limit
        
        logger.info(f"[QdrantRetriever] 查找与文档 {document_id} 相似的文档")
        
        try:
            # 获取原文档的向量
            # 注意：这里需要实现从Qdrant获取特定文档向量的功能
            # 当前简化处理，使用随机向量
            import numpy as np
            query_vector = np.random.random(1024).tolist()
            
            results = self.search(
                query_vector=query_vector,
                limit=limit + (1 if exclude_self else 0)
            )
            
            # 排除自身
            if exclude_self:
                results = [r for r in results if str(r["id"]) != str(document_id)][:limit]
            
            logger.info(
                f"[QdrantRetriever] 找到 {len(results)} 个相似文档"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[QdrantRetriever] 获取相似文档失败: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检索器统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            collection_info = self.client.get_collection_info(self.collection_name)
            
            stats = {
                "collection_name": self.collection_name,
                "total_documents": collection_info["points_count"],
                "vector_dimension": collection_info["vector_size"],
                "distance_function": collection_info["distance"],
                "status": collection_info["status"],
                "client_mode": self.client.mode,
                "client_connected": self.client.is_connected
            }
            
            logger.info(f"[QdrantRetriever] 统计信息: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"[QdrantRetriever] 获取统计信息失败: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "error": str(e)
            }


def create_qdrant_retriever(
    collection_name: str = "german_parliament",
    qdrant_client: Optional[QdrantClient] = None
) -> QdrantRetriever:
    """
    创建Qdrant检索器实例
    
    Args:
        collection_name: 集合名称
        qdrant_client: Qdrant客户端 (如果为None，将创建新的)
        
    Returns:
        QdrantRetriever: 检索器实例
    """
    if qdrant_client is None:
        from .qdrant_client import create_qdrant_client
        qdrant_client = create_qdrant_client()
    
    return QdrantRetriever(
        qdrant_client=qdrant_client,
        collection_name=collection_name
    )


if __name__ == "__main__":
    # 测试代码
    import numpy as np
    from .qdrant_client import QdrantClient
    
    # 创建测试环境
    client = QdrantClient(mode="memory")
    client.create_collection_for_german_parliament("test_retriever")
    
    # 插入测试数据
    test_data = [
        {
            "id": i,
            "vector": np.random.random(1024).tolist(),
            "payload": {
                "text": f"测试文档 {i}",
                "year": 2019 + (i % 3),
                "party": ["CDU/CSU", "SPD", "FDP"][i % 3],
                "speaker": f"Speaker_{i}"
            }
        }
        for i in range(10)
    ]
    
    client.upsert_german_parliament_data("test_retriever", test_data)
    
    # 创建检索器
    retriever = QdrantRetriever(client, "test_retriever")
    
    # 测试搜索
    query_vector = np.random.random(1024).tolist()
    
    print("=== 基础搜索测试 ===")
    results = retriever.search(query_vector, limit=3)
    print(f"搜索结果: {len(results)} 个")
    
    print("=== 按党派搜索测试 ===")
    party_results = retriever.search_by_party(query_vector, "CDU/CSU", limit=3)
    print(f"CDU/CSU搜索结果: {len(party_results)} 个")
    
    print("=== 混合搜索测试 ===")
    hybrid_results = retriever.hybrid_search(
        query_vector, "测试", limit=3
    )
    print(f"混合搜索结果: {len(hybrid_results)} 个")
    
    print("=== 统计信息 ===")
    stats = retriever.get_statistics()
    print(f"统计信息: {stats}")
    
    client.close()
