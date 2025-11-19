"""
Milvus混合检索器模块
实现向量检索+元数据过滤
"""

from pymilvus import Collection
from typing import List, Dict, Any, Optional
from src.utils import logger


class MilvusRetriever:
    """
    Milvus混合检索器
    
    功能:
    1. 向量相似度检索
    2. 元数据过滤(年份、党派、议员等)
    3. 混合检索(向量+过滤)
    4. 结果排序和格式化
    """
    
    def __init__(
        self,
        collection: Collection,
        top_k: int = 10
    ):
        """
        初始化检索器
        
        Args:
            collection: Milvus Collection对象
            top_k: 返回结果数量
        """
        self.collection = collection
        self.top_k = top_k
        
        logger.info(f"初始化检索器: collection={collection.name}, top_k={top_k}")
    
    def search(
        self,
        query_vector: List[float],
        filter_expr: Optional[str] = None,
        top_k: Optional[int] = None,
        output_fields: List[str] = None
    ) -> List[Dict]:
        """
        混合检索
        
        Args:
            query_vector: 查询向量
            filter_expr: 过滤表达式(如: "year == '2020'")
            top_k: 返回数量
            output_fields: 返回字段列表
        
        Returns:
            检索结果列表
        """
        top_k = top_k or self.top_k
        output_fields = output_fields or [
            "text", "year", "month", "day",
            "speaker", "group", "group_chinese",
            "file", "chunk_id"
        ]
        
        # 搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        logger.info(
            f"执行检索: top_k={top_k}, "
            f"filter={'有' if filter_expr else '无'}"
        )
        
        # 执行搜索
        results = self.collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=output_fields
        )
        
        # 格式化结果
        formatted_results = self._format_results(results[0])
        
        logger.info(f"检索完成: 返回{len(formatted_results)}条结果")
        
        return formatted_results
    
    def search_by_metadata(
        self,
        query_vector: List[float],
        year: Optional[str] = None,
        year_range: Optional[tuple] = None,
        party: Optional[str] = None,
        speaker: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        基于元数据的混合检索
        
        Args:
            query_vector: 查询向量
            year: 年份
            year_range: 年份范围(start, end)
            party: 党派
            speaker: 议员
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        # 构建过滤表达式
        filters = []
        
        if year:
            filters.append(f'year == "{year}"')
        
        if year_range:
            start, end = year_range
            filters.append(f'year >= "{start}" and year <= "{end}"')
        
        if party:
            filters.append(f'group == "{party}"')
        
        if speaker:
            filters.append(f'speaker == "{speaker}"')
        
        # 组合过滤条件
        filter_expr = " and ".join(filters) if filters else None
        
        logger.debug(f"元数据过滤: {filter_expr}")
        
        # 执行检索
        return self.search(
            query_vector=query_vector,
            filter_expr=filter_expr,
            top_k=top_k
        )
    
    def _format_results(self, raw_results) -> List[Dict]:
        """
        格式化检索结果
        
        Args:
            raw_results: Milvus原始结果
        
        Returns:
            格式化后的结果列表
        """
        formatted = []
        
        for hit in raw_results:
            result = {
                'id': hit.id,
                'distance': hit.distance,
                'score': 1 / (1 + hit.distance),  # 转换为相似度分数
            }
            
            # 添加entity字段（兼容不同版本的Milvus API）
            try:
                # 新版本API
                if hasattr(hit.entity, '_row_data'):
                    for field, value in hit.entity._row_data.items():
                        result[field] = value
                # 备用方法：直接访问entity属性
                elif hasattr(hit, 'entity'):
                    # 尝试获取常见字段
                    common_fields = ['id', 'text', 'chunk_text', 'metadata', 'speaker', 'party', 'session_date']
                    for field in common_fields:
                        if hasattr(hit.entity, field):
                            result[field] = getattr(hit.entity, field)
                        # 也尝试通过索引访问
                        try:
                            if hasattr(hit.entity, 'get'):
                                value = hit.entity.get(field)
                                if value is not None:
                                    result[field] = value
                        except:
                            pass
                # 最后尝试直接从hit对象获取
                else:
                    # 直接访问hit的其他属性
                    for attr_name in dir(hit):
                        if not attr_name.startswith('_') and attr_name not in ['distance', 'id']:
                            try:
                                value = getattr(hit, attr_name)
                                if not callable(value):
                                    result[attr_name] = value
                            except:
                                pass
            except Exception as e:
                logger.warning(f"获取entity字段时出错: {e}")
                # 至少确保有基本字段
                result['text'] = f"检索结果 (ID: {hit.id})"
                result['metadata'] = {}
            
            formatted.append(result)
        
        return formatted


if __name__ == "__main__":
    print("检索器测试需要先创建Collection并插入数据")
    print("请参考完整的端到端测试脚本")
