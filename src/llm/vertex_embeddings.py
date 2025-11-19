"""
Vertex AI Embedding 客户端
使用 Google Cloud Vertex AI 的 text-embedding-004 模型
"""

import os
import vertexai
from vertexai.language_models import TextEmbeddingModel
from typing import List
from src.utils import logger


class VertexAIEmbeddingClient:
    """
    Vertex AI Embedding 客户端
    
    使用 Google Cloud 的 Vertex AI 进行文本向量化
    需要设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量
    """
    
    def __init__(
        self,
        project_id: str = "heroic-cedar-476803-e1",
        location: str = "us-central1",
        model_name: str = "text-embedding-004"
    ):
        """
        初始化 Vertex AI Embedding 客户端
        
        Args:
            project_id: Google Cloud 项目 ID
            location: 区域（us-central1, asia-southeast1 等）
            model_name: 模型名称（text-embedding-004）
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.dimensions = 768  # text-embedding-004 的维度
        
        # 检查环境变量
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            logger.warning("⚠️  未设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
            logger.warning("   请运行: set GOOGLE_APPLICATION_CREDENTIALS=heroic-cedar-476803-e1-fe50591663ce.json")
        else:
            logger.info(f"✅ 找到凭证文件: {credentials_path}")
        
        # 初始化 Vertex AI
        try:
            logger.info(f"🔄 初始化 Vertex AI: project={project_id}, location={location}")
            vertexai.init(project=project_id, location=location)
            
            # 加载模型
            logger.info(f"🔄 加载模型: {model_name}")
            self.model = TextEmbeddingModel.from_pretrained(model_name)
            
            logger.success(f"✅ Vertex AI Embedding 初始化成功！")
            logger.info(f"📊 模型: {model_name}, 向量维度: {self.dimensions}")
            
        except Exception as e:
            logger.error(f"❌ Vertex AI 初始化失败: {e}")
            logger.error("请检查:")
            logger.error("1. GOOGLE_APPLICATION_CREDENTIALS 环境变量是否正确")
            logger.error("2. JSON 凭证文件是否存在")
            logger.error("3. Google Cloud 项目是否启用了 Vertex AI API")
            logger.error("4. 服务账号是否有足够的权限")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        单文本 embedding
        
        Args:
            text: 输入文本
            
        Returns:
            向量（768维）
        """
        try:
            # 调用 Vertex AI
            embeddings = self.model.get_embeddings([text])
            vector = embeddings[0].values
            
            logger.debug(
                f"文本 embedding 成功: 文本长度={len(text)}, "
                f"向量维度={len(vector)}"
            )
            
            return vector
            
        except Exception as e:
            logger.error(f"文本 embedding 失败: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本 embedding
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        try:
            # Vertex AI 支持批量处理
            embeddings = self.model.get_embeddings(texts)
            vectors = [emb.values for emb in embeddings]
            
            logger.debug(
                f"批量 embedding 成功: {len(texts)} 个文本 -> "
                f"{len(vectors)} 个向量"
            )
            
            return vectors
            
        except Exception as e:
            logger.error(f"批量 embedding 失败: {e}")
            raise
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 5
    ) -> List[List[float]]:
        """
        分批处理（Vertex AI 有速率限制）
        
        Args:
            texts: 文本列表
            batch_size: 批次大小（建议 5-10）
            
        Returns:
            向量列表
        """
        logger.info(f"📦 批量 embedding: {len(texts)} 个文本")
        
        all_vectors = []
        
        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            logger.debug(
                f"处理批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}: "
                f"{len(batch)} 个文本"
            )
            
            # 调用 API
            vectors = self.embed_documents(batch)
            all_vectors.extend(vectors)
        
        logger.success(f"✅ 批量 embedding 完成: {len(all_vectors)} 个向量")
        
        return all_vectors
    
    def embed_chunks(
        self,
        chunks: List[dict],
        text_key: str = 'text',
        batch_size: int = 5
    ) -> List[dict]:
        """
        对 chunks 进行批量 embedding
        
        Args:
            chunks: chunk 字典列表
            text_key: 文本字段名
            batch_size: 批次大小
            
        Returns:
            添加了 vector 字段的 chunks
        """
        logger.info(f"📚 开始对 {len(chunks)} 个 chunks 进行 embedding")
        
        # 提取文本
        texts = [chunk[text_key] for chunk in chunks]
        
        # 批量 embedding
        vectors = self.embed_batch(texts, batch_size)
        
        # 添加向量到 chunks
        embedded_chunks = []
        for chunk, vector in zip(chunks, vectors):
            embedded_chunk = chunk.copy()
            embedded_chunk['vector'] = vector
            embedded_chunks.append(embedded_chunk)
        
        logger.success(f"✅ Chunks embedding 完成: {len(embedded_chunks)} 个")
        
        return embedded_chunks


if __name__ == "__main__":
    # 测试 Vertex AI Embedding
    print("\n" + "="*80)
    print("测试 Vertex AI Embedding")
    print("="*80)
    
    # 检查环境变量
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"\n环境变量 GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")
    
    if not credentials_path:
        print("\n❌ 错误: 未设置环境变量")
        print("\n请在 PowerShell 中运行:")
        print('  $env:GOOGLE_APPLICATION_CREDENTIALS="f:\\vscode_project\\tj_germany\\heroic-cedar-476803-e1-fe50591663ce.json"')
        print("\n或在 CMD 中运行:")
        print('  set GOOGLE_APPLICATION_CREDENTIALS=f:\\vscode_project\\tj_germany\\heroic-cedar-476803-e1-fe50591663ce.json')
        exit(1)
    
    try:
        # 初始化客户端
        print("\n初始化 Vertex AI 客户端...")
        client = VertexAIEmbeddingClient()
        
        # 测试1: 中文文本
        print("\n" + "-"*80)
        print("测试1: 中文文本")
        print("-"*80)
        text_cn = "德国联邦议院是德国的最高立法机构。"
        vector_cn = client.embed_query(text_cn)
        print(f"文本: {text_cn}")
        print(f"向量维度: {len(vector_cn)}")
        print(f"向量前5维: {vector_cn[:5]}")
        
        # 测试2: 德语文本
        print("\n" + "-"*80)
        print("测试2: 德语文本")
        print("-"*80)
        text_de = "Der Deutsche Bundestag ist das Parlament."
        vector_de = client.embed_query(text_de)
        print(f"文本: {text_de}")
        print(f"向量维度: {len(vector_de)}")
        print(f"向量前5维: {vector_de[:5]}")
        
        # 测试3: 批量处理
        print("\n" + "-"*80)
        print("测试3: 批量处理")
        print("-"*80)
        texts = [
            "社民党是德国历史最悠久的政党之一。",
            "基民盟在德国政治中扮演重要角色。",
            "绿党关注环境和气候问题。"
        ]
        vectors = client.embed_batch(texts, batch_size=2)
        print(f"批量处理: {len(texts)} 个文本 -> {len(vectors)} 个向量")
        for i, (text, vector) in enumerate(zip(texts, vectors), 1):
            print(f"\n文本{i}: {text}")
            print(f"  向量维度: {len(vector)}")
            print(f"  向量前3维: {vector[:3]}")
        
        print("\n" + "="*80)
        print("✅ 所有测试通过！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
