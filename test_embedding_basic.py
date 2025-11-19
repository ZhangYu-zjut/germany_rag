#!/usr/bin/env python3
"""
测试基础embedding功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.utils.logger import setup_logger

logger = setup_logger()

def test_embedding_minimal():
    """最小化embedding测试"""
    
    logger.info("🧪 开始最小化embedding测试")
    
    try:
        # 测试1: 导入模块
        logger.info("1️⃣ 测试导入...")
        from src.llm.embeddings import GeminiEmbeddingClient
        logger.info("✅ 模块导入成功")
        
        # 测试2: 初始化客户端
        logger.info("2️⃣ 测试客户端初始化...")
        client = GeminiEmbeddingClient(embedding_mode="local")
        logger.info("✅ 客户端初始化成功")
        
        # 测试3: 单个文本embedding
        logger.info("3️⃣ 测试单个文本embedding...")
        test_text = "这是一个简单的测试文本。"
        embedding = client.embed_text(test_text)
        logger.info(f"✅ Embedding成功: 维度={len(embedding)}")
        
        # 测试4: 小批量embedding
        logger.info("4️⃣ 测试小批量embedding...")
        test_texts = [
            "德国议会讨论了重要议题。",
            "这是第二个测试文本。",
            "今天天气很好。"
        ]
        embeddings = client.embed_batch(test_texts, batch_size=3)
        logger.info(f"✅ 批量embedding成功: {len(embeddings)}个向量")
        
        logger.info("🎉 所有embedding测试通过!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Embedding测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_embedding_minimal()
    if success:
        print("\n✅ Embedding功能正常，可以继续数据迁移")
    else:
        print("\n❌ Embedding功能异常，需要解决后再进行迁移")
        sys.exit(1)
