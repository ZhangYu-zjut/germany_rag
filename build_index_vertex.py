"""
索引构建脚本（使用 Vertex AI Embedding）
使用 Google Cloud Vertex AI 的 text-embedding-004 模型
"""

import os
from src.data_loader import ParliamentDataLoader, ParliamentTextSplitter, MetadataMapper
from src.llm.vertex_embeddings import VertexAIEmbeddingClient
from src.vectordb import MilvusClient, MilvusCollectionManager
from src.utils import logger


def main():
    """主函数"""
    print("="*80)
    print("德国议会智能问答系统 - 索引构建（Vertex AI Embedding）")
    print("="*80)
    
    # ========== 检查环境变量 ==========
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        print("\n❌ 错误: 未设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
        print("\n请在 PowerShell 中运行:")
        print('  $env:GOOGLE_APPLICATION_CREDENTIALS="f:\\vscode_project\\tj_germany\\heroic-cedar-476803-e1-fe50591663ce.json"')
        print("\n或在 CMD 中运行:")
        print('  set GOOGLE_APPLICATION_CREDENTIALS=f:\\vscode_project\\tj_germany\\heroic-cedar-476803-e1-fe50591663ce.json')
        print("\n然后重新运行此脚本")
        return
    
    print(f"\n✅ 找到凭证文件: {credentials_path}")
    
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
    
    # ========== 第 4 步：生成向量 (Vertex AI) ==========
    print("\n[4/5] 生成向量（使用 Vertex AI）...")
    
    try:
        embedding_client = VertexAIEmbeddingClient()
    except Exception as e:
        logger.error(f"❌ Vertex AI 初始化失败: {e}")
        print("\n请检查:")
        print("1. GOOGLE_APPLICATION_CREDENTIALS 环境变量是否正确")
        print("2. JSON 凭证文件是否存在")
        print("3. Google Cloud 项目是否启用了 Vertex AI API")
        print("4. 服务账号是否有足够的权限")
        return
    
    # 批量 Embedding
    logger.info("开始批量 Embedding...")
    embedded_chunks = embedding_client.embed_chunks(
        chunks,
        batch_size=5  # Vertex AI 建议小批次
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
    print(f"  - Embedding 模型: Vertex AI text-embedding-004")
    print(f"\n🎉 现在可以运行 python main.py 开始问答！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        raise
