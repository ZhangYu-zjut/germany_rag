"""
Milvus Collection管理模块
负责创建、管理Collection和索引
"""

from pymilvus import (
    Collection, CollectionSchema, FieldSchema,
    DataType, utility
)
from typing import List, Dict, Any, Optional
from src.config import settings
from src.utils import logger


class MilvusCollectionManager:
    """
    Milvus Collection管理器
    
    功能:
    1. 创建/删除Collection
    2. 创建索引
    3. 数据插入
    4. Collection状态管理
    """
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        alias: str = "default"
    ):
        """
        初始化Collection管理器
        
        Args:
            collection_name: Collection名称,默认从配置读取
            alias: Milvus连接别名
        """
        self.collection_name = collection_name or settings.milvus_collection_name
        self.alias = alias
        self.collection: Optional[Collection] = None
        
        logger.info(f"初始化Collection管理器: {self.collection_name}")
    
    def create_collection(
        self,
        dimension: int = None,
        description: str = "German Parliament Speeches Collection"
    ):
        """
        创建Collection
        
        Args:
            dimension: 向量维度,默认从配置读取
            description: Collection描述
        """
        dimension = dimension or settings.embedding_dimension
        
        # 检查是否已存在
        if utility.has_collection(self.collection_name, using=self.alias):
            logger.warning(f"Collection已存在: {self.collection_name}")
            self.collection = Collection(
                name=self.collection_name,
                using=self.alias
            )
            return
        
        logger.info(f"创建Collection: {self.collection_name}, dimension={dimension}")
        
        # 定义Schema
        fields = [
            # 主键
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
                description="Primary Key"
            ),
            
            # 向量字段
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="Text embedding vector"
            ),
            
            # 文本内容
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Speech text content"
            ),
            
            # === Metadata字段 ===
            
            # 时间相关
            FieldSchema(
                name="year",
                dtype=DataType.VARCHAR,
                max_length=4,
                description="Year"
            ),
            FieldSchema(
                name="month",
                dtype=DataType.VARCHAR,
                max_length=2,
                description="Month"
            ),
            FieldSchema(
                name="day",
                dtype=DataType.VARCHAR,
                max_length=2,
                description="Day"
            ),
            FieldSchema(
                name="session",
                dtype=DataType.VARCHAR,
                max_length=10,
                description="Session number"
            ),
            
            # 人物和党派
            FieldSchema(
                name="speaker",
                dtype=DataType.VARCHAR,
                max_length=200,
                description="Speaker name"
            ),
            FieldSchema(
                name="group",
                dtype=DataType.VARCHAR,
                max_length=100,
                description="Party group (German)"
            ),
            FieldSchema(
                name="group_chinese",
                dtype=DataType.VARCHAR,
                max_length=100,
                description="Party group (Chinese)"
            ),
            
            # 文件信息
            FieldSchema(
                name="file",
                dtype=DataType.VARCHAR,
                max_length=50,
                description="Source file name"
            ),
            FieldSchema(
                name="lp",
                dtype=DataType.VARCHAR,
                max_length=10,
                description="Legislative period"
            ),
            
            # Chunk信息
            FieldSchema(
                name="chunk_id",
                dtype=DataType.INT32,
                description="Chunk ID within speech"
            ),
            FieldSchema(
                name="total_chunks",
                dtype=DataType.INT32,
                description="Total chunks in speech"
            )
        ]
        
        # 创建Schema
        schema = CollectionSchema(
            fields=fields,
            description=description
        )
        
        # 创建Collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema,
            using=self.alias
        )
        
        logger.success(f"Collection创建成功: {self.collection_name}")
    
    def create_index(
        self,
        index_type: str = "IVF_FLAT",
        metric_type: str = "L2",
        nlist: int = 1024
    ):
        """
        为向量字段创建索引
        
        Args:
            index_type: 索引类型(IVF_FLAT, IVF_SQ8, HNSW等)
            metric_type: 距离度量(L2, IP, COSINE)
            nlist: 聚类中心数量
        """
        if not self.collection:
            raise ValueError("Collection未初始化")
        
        logger.info(
            f"创建索引: type={index_type}, "
            f"metric={metric_type}, nlist={nlist}"
        )
        
        # 定义索引参数
        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": {"nlist": nlist}
        }
        
        # 创建索引
        self.collection.create_index(
            field_name="vector",
            index_params=index_params
        )
        
        logger.success("索引创建成功")
    
    def insert_data(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 5000
    ) -> List[int]:
        """
        批量插入数据（分批插入，避免gRPC消息大小限制）
        
        Args:
            chunks: chunk列表,每个chunk包含vector, text, metadata
            batch_size: 每批插入的数量，默认5000条（避免gRPC消息大小限制256MB）
        
        Returns:
            插入的ID列表
        """
        if not self.collection:
            raise ValueError("Collection未初始化")
        
        total = len(chunks)
        logger.info(f"准备插入数据: {total}条，分批大小: {batch_size}条/批")
        
        all_ids = []
        total_batches = (total + batch_size - 1) // batch_size
        
        # 分批插入（使用tqdm显示进度）
        try:
            from tqdm import tqdm
            use_tqdm = True
        except ImportError:
            use_tqdm = False
        
        iterator = range(0, total, batch_size)
        if use_tqdm:
            iterator = tqdm(iterator, desc="插入数据", unit="批", total=total_batches)
        
        # 分批插入
        for i in iterator:
            batch_num = i // batch_size + 1
            batch_chunks = chunks[i:i + batch_size]
            
            if not use_tqdm:
                logger.info(f"插入批次 {batch_num}/{total_batches}: {len(batch_chunks)}条 (总计: {i+len(batch_chunks)}/{total})")
            
            try:
                # 准备当前批次数据
                batch_data = self._prepare_insert_data(batch_chunks)
                
                # 插入当前批次
                insert_result = self.collection.insert(batch_data)
                
                # 收集ID
                all_ids.extend(insert_result.primary_keys)
                
                if not use_tqdm:
                    logger.debug(f"批次 {batch_num} 插入成功: {len(insert_result.primary_keys)}条")
                
            except Exception as e:
                logger.error(f"批次 {batch_num} 插入失败: {str(e)}")
                raise
        
        # 所有批次插入完成后，刷新以确保数据持久化
        logger.info("刷新数据以确保持久化...")
        self.collection.flush()
        
        logger.success(f"数据插入成功: 共{len(all_ids)}条，分{total_batches}批完成")
        
        return all_ids
    
    def _prepare_insert_data(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[List]:
        """
        准备插入数据的格式
        
        Args:
            chunks: chunk列表
        
        Returns:
            按字段组织的数据列表
        """
        # 按字段提取数据
        vectors = []
        texts = []
        years = []
        months = []
        days = []
        sessions = []
        speakers = []
        groups = []
        groups_chinese = []
        files = []
        lps = []
        chunk_ids = []
        total_chunks_list = []
        
        for chunk in chunks:
            vector = chunk.get('vector', [])
            text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            
            vectors.append(vector)
            texts.append(text[:65535])  # 限制长度
            years.append(metadata.get('year', '')[:4])
            months.append(metadata.get('month', '')[:2])
            days.append(metadata.get('day', '')[:2])
            sessions.append(metadata.get('session', '')[:10])
            speakers.append(metadata.get('speaker', '')[:200])
            groups.append(metadata.get('group', '')[:100])
            groups_chinese.append(metadata.get('group_chinese', '')[:100])
            files.append(metadata.get('file', '')[:50])
            lps.append(metadata.get('lp', '')[:10])
            chunk_ids.append(metadata.get('chunk_id', 0))
            total_chunks_list.append(metadata.get('total_chunks', 1))
        
        # 返回按字段组织的数据
        return [
            vectors,
            texts,
            years,
            months,
            days,
            sessions,
            speakers,
            groups,
            groups_chinese,
            files,
            lps,
            chunk_ids,
            total_chunks_list
        ]
    
    def load_collection(self):
        """加载Collection到内存"""
        if not self.collection:
            raise ValueError("Collection未初始化")
        
        self.collection.load()
        logger.info(f"Collection已加载: {self.collection_name}")
    
    def get_collection_stats(self) -> Dict:
        """
        获取Collection统计信息
        
        Returns:
            统计信息字典
        """
        if not self.collection:
            raise ValueError("Collection未初始化")
        
        stats = {
            'name': self.collection_name,
            'num_entities': self.collection.num_entities,
            'schema': str(self.collection.schema)
        }
        
        logger.info(f"Collection统计: {self.collection_name}, entities={stats['num_entities']}")
        
        return stats
    
    def drop_collection(self):
        """删除Collection"""
        utility.drop_collection(self.collection_name, using=self.alias)
        self.collection = None
        logger.warning(f"Collection已删除: {self.collection_name}")


if __name__ == "__main__":
    from src.vectordb.client import MilvusClient
    
    print("\n=== Collection管理器测试 ===")
    
    # 连接Milvus
    try:
        with MilvusClient() as client:
            # 创建Collection管理器
            manager = MilvusCollectionManager()
            
            # 创建Collection
            manager.create_collection(dimension=1536)
            
            # 创建索引
            manager.create_index()
            
            # 获取统计信息
            stats = manager.get_collection_stats()
            print(f"\nCollection统计: {stats}")
            
    except Exception as e:
        print(f"测试失败: {e}")

