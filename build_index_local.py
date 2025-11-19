"""
索引构建脚本（使用本地 Embedding）
如果 API Embedding 失败，使用此脚本
"""

from src.data_loader import ParliamentDataLoader, ParliamentTextSplitter, MetadataMapper
from src.llm.local_embeddings import LocalEmbeddingClient  # 使用本地模型
from src.vectordb import MilvusClient, MilvusCollectionManager
from src.utils import logger
from tqdm import tqdm


def main():
    """主函数"""
    print("="*80)
    print("德国议会智能问答系统 - 索引构建（本地 Embedding）")
    print("="*80)
    
    # ========== 第 1 步：加载数据 ==========
    print("\n[1/5] 加载议会演讲数据...")
    loader = ParliamentDataLoader()
    speeches = loader.load_data()
    
    # 限制处理数量（可选，用于快速测试）
    # sample_size = 100
    # speeches = speeches[:sample_size]
    # logger.info(f"限制处理数量: {sample_size}")
    
    logger.info(f"加载了 {len(speeches)} 条演讲记录")
    
    # ========== 第 2 步：文本分块 ==========
    print("\n[2/5] 文本分块...")
    splitter = ParliamentTextSplitter()
    chunks = splitter.split_speeches(speeches)
    logger.info(f"生成了 {len(chunks)} 个文本块")
    
    # ========== 第 3 步：元数据丰富 ==========
    print("\n[3/5] 元数据映射和丰富...")
    mapper = MetadataMapper()
    chunks = mapper.enrich_chunks(chunks)
    logger.info(f"元数据丰富完成")
    
    # ========== 第 4 步：生成向量 (本地模型) ==========
    print("\n[4/5] 生成向量（使用本地模型）...")
    print("⏳ 首次运行需要下载模型（~200MB），请稍候...")
    
    embedding_client = LocalEmbeddingClient()
    
    # 批量 Embedding
    logger.info("开始批量 Embedding...")
    embedded_chunks = embedding_client.embed_chunks(
        chunks,
        batch_size=32  # 本地模型可以用更大的批次
    )
    
    logger.success(f"✅ Embedding 完成: {len(embedded_chunks)} 个向量")
    
    # 获取实际向量维度
    actual_dim = len(embedded_chunks[0]['vector'])
    logger.info(f"📊 向量维度: {actual_dim}")
    
    # ========== 第 5 步：存储到 Milvus ==========
    print("\n[5/5] 存储到 Milvus...")
    
    # 连接 Milvus
    with MilvusClient() as client:
        # 创建 Collection Manager（使用实际维度）
        manager = MilvusCollectionManager(vector_dim=actual_dim)
        
        # 插入数据
        logger.info("开始插入数据到 Milvus...")
        manager.insert_data(embedded_chunks)
        
        # 创建索引
        logger.info("创建索引...")
        manager.create_index()
        
        # 加载到内存
        logger.info("加载 Collection 到内存...")
        manager.collection.load()
        
        # 验证
        count = manager.collection.num_entities
        logger.success(f"✅ 数据插入完成: {count} 条记录")
    
    print("\n" + "="*80)
    print("✅ 索引构建完成！")
    print("="*80)
    print(f"\n📊 统计信息:")
    print(f"  - 演讲记录: {len(speeches)} 条")
    print(f"  - 文本块: {len(chunks)} 个")
    print(f"  - 向量维度: {actual_dim}")
    print(f"  - 向量数量: {count} 个")
    print(f"\n🎉 现在可以运行 python main.py 开始问答！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        raise
