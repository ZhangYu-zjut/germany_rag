"""
端到端数据处理和索引构建脚本
演示完整的数据加载->分块->Embedding->存储流程
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.utils import logger
from src.data_loader import ParliamentDataLoader, ParliamentTextSplitter, MetadataMapper
from src.llm import GeminiEmbeddingClient
from src.vectordb import MilvusClient, MilvusCollectionManager


def main():
    """
    主流程:
    1. 加载数据
    2. 文本分块
    3. 丰富元数据
    4. 生成Embedding
    5. 存储到Milvus
    """
    
    logger.info("="*80)
    logger.info("开始执行端到端数据处理和索引构建")
    logger.info("="*80)
    
    # ========== 步骤1: 加载数据 ==========
    logger.info("\n步骤1: 加载数据")
    logger.info("-" * 40)
    
    loader = ParliamentDataLoader()
    speeches = loader.load_data()
    logger.info(f"加载完成: {len(speeches)}条演讲")
    
    # 获取统计信息
    stats = loader.get_statistics(speeches)
    
    # ========== 步骤2: 文本分块 ==========
    logger.info("\n步骤2: 文本分块")
    logger.info("-" * 40)
    
    # 从环境变量读取分块配置
    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    splitter = ParliamentTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    # 为了演示,先处理部分数据
    sample_size = 100  # 可根据需要调整
    logger.info(f"处理前{sample_size}条演讲(可修改sample_size处理更多)")
    
    chunks = splitter.split_speeches(speeches[:sample_size])
    logger.info(f"分块完成: {len(chunks)}个chunks")
    
    # 获取分块统计
    chunk_stats = splitter.get_chunk_statistics(chunks)
    
    # ========== 步骤3: 丰富元数据 ==========
    logger.info("\n步骤3: 丰富元数据")
    logger.info("-" * 40)
    
    mapper = MetadataMapper()
    enriched_chunks = mapper.batch_enrich_chunks(chunks)
    logger.info(f"元数据丰富完成: {len(enriched_chunks)}个chunks")
    
    # 显示示例
    logger.info("\n示例chunk:")
    example = enriched_chunks[0]
    logger.info(f"  发言人: {example['metadata'].get('speaker')}")
    logger.info(f"  党派(德): {example['metadata'].get('group')}")
    logger.info(f"  党派(中): {example['metadata'].get('group_chinese')}")
    logger.info(f"  年份: {example['metadata'].get('year')}")
    logger.info(f"  文本长度: {len(example['text'])} 字符")
    
    # ========== 步骤4: 生成Embedding ==========
    logger.info("\n步骤4: 生成Embedding")
    logger.info("-" * 40)
    
    # 从环境变量读取Embedding模式
    embedding_mode = os.getenv("EMBEDDING_MODE", "openai").lower()
    print(f"🔍 检测到Embedding模式: {embedding_mode}")
    
    # 根据配置选择Embedding客户端
    if embedding_mode == "local":
        logger.info("📦 使用本地Embedding模型（免费、离线）")
        local_model = os.getenv("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        embedding_client = LocalEmbeddingClient(local_model)
    elif embedding_mode == "openai":
        logger.info("☁️  使用OpenAI官方Embedding API")
        embedding_client = GeminiEmbeddingClient(use_official_api=True)
    else:  # vertex
        logger.info("☁️  使用Vertex AI Embedding")
        from src.llm.vertex_embeddings import VertexAIEmbeddingClient
        embedding_client = VertexAIEmbeddingClient()
    
    # 批量生成embedding
    logger.info("开始批量Embedding...")
    embedded_chunks = embedding_client.embed_chunks(
        enriched_chunks,
        batch_size=50
    )
    logger.info(f"Embedding完成: {len(embedded_chunks)}个chunks")
    
    # 验证embedding
    logger.info(f"向量维度: {len(embedded_chunks[0]['vector'])}")
    
    # ========== 步骤5: 存储到Milvus ==========
    logger.info("\n步骤5: 存储到Milvus")
    logger.info("-" * 40)
    
    try:
        # 连接Milvus
        with MilvusClient() as milvus_client:
            logger.info("Milvus连接成功")
            
            # 创建Collection管理器
            collection_manager = MilvusCollectionManager()
            
            # 创建Collection
            collection_manager.create_collection()
            
            # 创建索引
            collection_manager.create_index()
            
            # 插入数据
            logger.info("开始插入数据...")
            ids = collection_manager.insert_data(embedded_chunks)
            logger.info(f"数据插入完成: {len(ids)}条")
            
            # 加载Collection
            collection_manager.load_collection()
            
            # 获取统计信息
            collection_stats = collection_manager.get_collection_stats()
            logger.info(f"\nCollection统计:")
            logger.info(f"  名称: {collection_stats['name']}")
            logger.info(f"  数据量: {collection_stats['num_entities']}条")
    
    except Exception as e:
        logger.error(f"Milvus操作失败: {e}")
        logger.warning("请确保Milvus服务正在运行")
        logger.info("Docker启动命令: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest")
        return
    
    # ========== 完成 ==========
    logger.info("\n" + "="*80)
    logger.success("端到端处理完成!")
    logger.info("="*80)
    
    # 获取向量维度
    vector_dim = len(embedded_chunks[0]['vector'])
    milvus_mode = os.getenv("MILVUS_MODE", "lite")
    collection_name = os.getenv("MILVUS_COLLECTION_NAME", "german_parliament_speeches")
    
    logger.info("\n处理摘要:")
    logger.info(f"  原始演讲数: {len(speeches)}")
    logger.info(f"  处理演讲数: {sample_size}")
    logger.info(f"  生成chunks: {len(embedded_chunks)}")
    logger.info(f"  向量维度: {vector_dim}")
    logger.info(f"  存储位置: Milvus ({milvus_mode}模式)")
    logger.info(f"  Collection: {collection_name}")
    
    logger.info("\n下一步:")
    logger.info("  1. 可以增加sample_size处理更多数据")
    logger.info("  2. 运行测试脚本验证检索功能")
    logger.info("  3. 开始开发LangGraph工作流")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n用户中断执行")
    except Exception as e:
        logger.error(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
