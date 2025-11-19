"""
Qdrant向量数据库客户端封装
支持本地嵌入式模式和云端模式，提供连接管理和重试机制
"""

import os
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from qdrant_client import QdrantClient as QdrantClientBase
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, 
    Filter, FieldCondition, MatchValue, Range
)
from qdrant_client.http.exceptions import ResponseHandlingException

from ..utils.logger import logger


class QdrantClient:
    """
    Qdrant客户端封装类
    提供连接管理、重试机制和德国议会数据专用方法
    """
    
    def __init__(
        self,
        mode: str = "memory",  # "memory", "local", "cloud"
        local_path: Optional[str] = None,
        cloud_url: Optional[str] = None,
        cloud_api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化Qdrant客户端
        
        Args:
            mode: 运行模式 ("memory", "local", "cloud")
            local_path: 本地存储路径 (local模式)
            cloud_url: 云端服务URL (cloud模式)
            cloud_api_key: 云端API密钥 (cloud模式)
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
        """
        self.mode = mode
        self.local_path = local_path
        self.cloud_url = cloud_url
        self.cloud_api_key = cloud_api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = None
        self.is_connected = False
        
        logger.info(f"[QdrantClient] 初始化客户端，模式: {mode}")
        self._connect()
    
    def _connect(self) -> None:
        """建立Qdrant连接"""
        try:
            if self.mode == "memory":
                # 内存模式 (最适合WSL2开发)
                self._client = QdrantClientBase(":memory:")
                logger.info("[QdrantClient] 内存模式连接成功")
                
            elif self.mode == "local":
                # 本地文件模式
                if not self.local_path:
                    self.local_path = "./data/qdrant"
                
                # 确保目录存在
                Path(self.local_path).mkdir(parents=True, exist_ok=True)
                self._client = QdrantClientBase(path=self.local_path)
                logger.info(f"[QdrantClient] 本地模式连接成功: {self.local_path}")
                
            elif self.mode == "cloud":
                # 云端模式
                if not self.cloud_url or not self.cloud_api_key:
                    raise ValueError("云端模式需要提供 cloud_url 和 cloud_api_key")
                
                self._client = QdrantClientBase(
                    url=self.cloud_url,
                    api_key=self.cloud_api_key
                )
                logger.info(f"[QdrantClient] 云端模式连接成功: {self.cloud_url}")
                
            else:
                raise ValueError(f"不支持的模式: {self.mode}")
            
            self.is_connected = True
            logger.info("[QdrantClient] 客户端初始化完成")
            
        except Exception as e:
            logger.error(f"[QdrantClient] 连接失败: {str(e)}")
            self.is_connected = False
            raise
    
    def ensure_connection(self) -> bool:
        """
        确保连接有效，如果断开则重连
        
        Returns:
            bool: 连接是否成功
        """
        if not self.is_connected or not self._client:
            logger.warning("[QdrantClient] 连接已断开，尝试重连...")
            try:
                self._connect()
                return True
            except Exception as e:
                logger.error(f"[QdrantClient] 重连失败: {str(e)}")
                return False
        return True
    
    def with_retry(self, operation_name: str):
        """
        装饰器：为操作提供重试机制
        
        Args:
            operation_name: 操作名称（用于日志）
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(self.max_retries):
                    try:
                        if not self.ensure_connection():
                            raise ConnectionError("无法建立Qdrant连接")
                        
                        return func(*args, **kwargs)
                        
                    except Exception as e:
                        last_exception = e
                        if attempt < self.max_retries - 1:
                            logger.warning(
                                f"[QdrantClient] {operation_name} 失败 "
                                f"(尝试 {attempt + 1}/{self.max_retries}): {str(e)}"
                            )
                            time.sleep(self.retry_delay * (2 ** attempt))  # 指数退避
                        else:
                            logger.error(
                                f"[QdrantClient] {operation_name} 最终失败: {str(e)}"
                            )
                
                raise last_exception
            return wrapper
        return decorator
    
    @property
    def client(self) -> QdrantClientBase:
        """获取底层Qdrant客户端"""
        if not self.ensure_connection():
            raise ConnectionError("Qdrant连接不可用")
        return self._client
    
    def create_collection_for_german_parliament(
        self, 
        collection_name: str = "german_parliament",
        vector_size: int = 1024,  # BGE-M3
        distance: Distance = Distance.COSINE,
        force_recreate: bool = False
    ) -> bool:
        """
        为德国议会数据创建专用集合
        
        Args:
            collection_name: 集合名称
            vector_size: 向量维度
            distance: 距离函数
            force_recreate: 是否强制重建
            
        Returns:
            bool: 创建是否成功
        """
        @self.with_retry(f"创建集合 {collection_name}")
        def _create_collection():
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == collection_name for c in collections)
            
            if collection_exists:
                if force_recreate:
                    logger.info(f"[QdrantClient] 删除现有集合: {collection_name}")
                    self.client.delete_collection(collection_name)
                else:
                    logger.info(f"[QdrantClient] 集合已存在: {collection_name}")
                    return True
            
            # 创建集合
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            
            logger.info(
                f"[QdrantClient] 集合创建成功: {collection_name} "
                f"(向量维度: {vector_size}, 距离函数: {distance})"
            )
            return True
        
        return _create_collection()
    
    def upsert_german_parliament_data(
        self,
        collection_name: str,
        data_points: List[Dict[str, Any]]
    ) -> bool:
        """
        插入德国议会数据
        
        Args:
            collection_name: 集合名称
            data_points: 数据点列表，格式:
                [{
                    "id": str|int,
                    "vector": List[float],
                    "payload": {
                        "text": str,
                        "year": int,
                        "month": int,
                        "party": str,
                        "speaker": str,
                        ...
                    }
                }]
                
        Returns:
            bool: 插入是否成功
        """
        @self.with_retry(f"插入数据到 {collection_name}")
        def _upsert_data():
            # 转换为PointStruct格式
            points = []
            for data in data_points:
                point = PointStruct(
                    id=data["id"],
                    vector=data["vector"],
                    payload=data["payload"]
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(
                f"[QdrantClient] 成功插入 {len(points)} 条数据到 {collection_name}"
            )
            return True
        
        return _upsert_data()
    
    def search_german_parliament(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        year_filter: Optional[Union[int, List[int]]] = None,
        party_filter: Optional[Union[str, List[str]]] = None,
        speaker_filter: Optional[Union[str, List[str]]] = None,
        topic_filter: Optional[Union[str, List[str]]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        德国议会数据专用搜索
        
        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            limit: 返回结果数量
            year_filter: 年份过滤
            party_filter: 党派过滤
            speaker_filter: 演讲者过滤
            topic_filter: 主题过滤
            score_threshold: 分数阈值
            
        Returns:
            List[Dict]: 搜索结果
        """
        @self.with_retry(f"搜索 {collection_name}")
        def _search():
            # 构建过滤条件
            must_conditions = []
            
            if year_filter is not None:
                if isinstance(year_filter, int):
                    must_conditions.append(
                        FieldCondition(key="year", match=MatchValue(value=year_filter))
                    )
                elif isinstance(year_filter, list):
                    must_conditions.append(
                        FieldCondition(key="year", match=MatchValue(value=year_filter[0]))
                    )  # 简化处理，可以扩展为范围查询
            
            if party_filter is not None:
                if isinstance(party_filter, str):
                    must_conditions.append(
                        FieldCondition(key="party", match=MatchValue(value=party_filter))
                    )
                elif isinstance(party_filter, list):
                    # 多党派OR查询 - 需要使用should条件
                    pass  # TODO: 实现多值匹配
            
            if speaker_filter is not None:
                if isinstance(speaker_filter, str):
                    must_conditions.append(
                        FieldCondition(key="speaker", match=MatchValue(value=speaker_filter))
                    )
            
            # 构建查询过滤器
            query_filter = None
            if must_conditions:
                query_filter = Filter(must=must_conditions)
            
            # 执行搜索 (使用新的query_points方法)
            search_results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )
            
            # 转换结果格式
            results = []
            for result in search_results.points:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                    "text": result.payload.get("text", ""),
                    "metadata": {k: v for k, v in result.payload.items() if k != "text"}
                })
            
            logger.info(
                f"[QdrantClient] 搜索完成，返回 {len(results)} 个结果 "
                f"(过滤条件: {len(must_conditions)} 个)"
            )
            return results
        
        return _search()
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合信息
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Dict: 集合信息
        """
        @self.with_retry(f"获取集合信息 {collection_name}")
        def _get_info():
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "points_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "status": info.status
            }
        
        return _get_info()
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 客户端是否健康
        """
        try:
            if not self.ensure_connection():
                return False
            
            # 简单的健康检查 - 获取集合列表
            collections = self.client.get_collections()
            logger.debug(f"[QdrantClient] 健康检查通过，找到 {len(collections.collections)} 个集合")
            return True
            
        except Exception as e:
            logger.error(f"[QdrantClient] 健康检查失败: {str(e)}")
            self.is_connected = False
            return False
    
    def close(self) -> None:
        """关闭连接"""
        if self._client:
            try:
                self._client.close()
                logger.info("[QdrantClient] 连接已关闭")
            except:
                pass
        self.is_connected = False
        self._client = None


# 工厂函数：根据环境变量创建客户端
def create_qdrant_client() -> QdrantClient:
    """
    根据环境变量创建Qdrant客户端
    
    环境变量:
        QDRANT_MODE: "memory" | "local" | "cloud"
        QDRANT_LOCAL_PATH: 本地存储路径
        QDRANT_CLOUD_URL: 云端URL
        QDRANT_CLOUD_API_KEY: 云端API密钥
    
    Returns:
        QdrantClient: 配置好的客户端实例
    """
    mode = os.getenv("QDRANT_MODE", "memory")
    local_path = os.getenv("QDRANT_LOCAL_PATH", "./data/qdrant")
    cloud_url = os.getenv("QDRANT_CLOUD_URL")
    cloud_api_key = os.getenv("QDRANT_CLOUD_API_KEY")
    
    logger.info(f"[QdrantClient] 创建客户端，模式: {mode}")
    
    return QdrantClient(
        mode=mode,
        local_path=local_path,
        cloud_url=cloud_url,
        cloud_api_key=cloud_api_key
    )


if __name__ == "__main__":
    # 测试代码
    import numpy as np
    
    # 创建测试客户端
    client = QdrantClient(mode="memory")
    
    # 创建集合
    client.create_collection_for_german_parliament("test_collection")
    
    # 插入测试数据
    test_data = [
        {
            "id": 1,
            "vector": np.random.random(1024).tolist(),
            "payload": {
                "text": "测试文本1",
                "year": 2019,
                "party": "CDU/CSU",
                "speaker": "Angela Merkel"
            }
        }
    ]
    
    client.upsert_german_parliament_data("test_collection", test_data)
    
    # 搜索测试
    results = client.search_german_parliament(
        "test_collection",
        np.random.random(1024).tolist(),
        limit=5,
        party_filter="CDU/CSU"
    )
    
    print(f"搜索结果: {len(results)} 个")
    
    # 健康检查
    is_healthy = client.health_check()
    print(f"健康状态: {is_healthy}")
    
    # 关闭连接
    client.close()
