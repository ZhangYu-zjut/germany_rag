"""
本地 Embedding 客户端
支持 sentence-transformers 和 BGE-M3 模型，完全免费，无需 API Key
支持 GPU 加速
"""

from typing import List, Optional
import torch
from src.utils import logger

# 尝试导入不同的模型库
try:
    from FlagEmbedding import BGEM3FlagModel
    FLAG_EMBEDDING_AVAILABLE = True
except ImportError:
    FLAG_EMBEDDING_AVAILABLE = False
    logger.warning("⚠️  FlagEmbedding 未安装，BGE-M3 模型不可用")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠️  sentence-transformers 未安装")


class LocalEmbeddingClient:
    """
    本地 Embedding 客户端
    
    优点:
    - ✅ 完全免费
    - ✅ 无需 API Key
    - ✅ 离线可用
    - ✅ 支持中文和德语
    - ✅ 支持 GPU 加速（如果有 GPU）
    - ✅ 支持 BGE-M3 模型（1024维，性能优异）
    
    支持的模型:
    - BGE-M3 系列（推荐）:
        - BAAI/bge-m3: 1024维，多语言支持，性能最佳
        - BAAI/bge-m3-base: 基础版本
    - sentence-transformers 模型:
        - paraphrase-multilingual-MiniLM-L12-v2: 384维，50+语言
        - distiluse-base-multilingual-cased-v2: 512维，15+语言
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_gpu: Optional[bool] = None,
        device: Optional[str] = None
    ):
        """
        初始化本地 Embedding 模型
        
        Args:
            model_name: 模型名称
                - BAAI/bge-m3: BGE-M3 模型，1024维 ⭐推荐（性能最佳）
                - BAAI/bge-m3-base: BGE-M3 基础版本
                - paraphrase-multilingual-MiniLM-L12-v2: sentence-transformers 模型，384维
                - distiluse-base-multilingual-cased-v2: sentence-transformers 模型，512维
            use_gpu: 是否使用 GPU（None 时自动检测）
            device: 指定设备（如 'cuda:0'），优先级高于 use_gpu
        """
        logger.info(f"🔄 加载本地 Embedding 模型: {model_name}")
        
        # 自动检测 GPU
        if device is None:
            if use_gpu is None:
                # 自动检测是否有可用的 GPU
                use_gpu = torch.cuda.is_available()
            device = 'cuda:0' if use_gpu else 'cpu'
        
        self.device = device
        self.model_name = model_name
        self.use_bge_m3 = False
        
        # 判断是否使用 BGE-M3 模型
        if 'bge-m3' in model_name.lower() or 'bge_m3' in model_name.lower():
            if not FLAG_EMBEDDING_AVAILABLE:
                raise ImportError(
                    "BGE-M3 模型需要 FlagEmbedding 库。请运行: pip install FlagEmbedding"
                )
            self.use_bge_m3 = True
            logger.info("🔧 使用 BGE-M3 模型（FlagEmbedding）")
            logger.info(f"   设备: {device}")
            logger.info("⏳ 加载本地缓存的 BGE-M3 模型，请稍候...")
            
            # 加载 BGE-M3 模型（离线模式）
            import os
            # 设置离线模式，避免网络请求
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            os.environ['HF_HUB_OFFLINE'] = '1'
            
            # 尝试使用本地缓存路径
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            model_cache_path = os.path.join(cache_dir, f"models--{model_name.replace('/', '--')}")
            
            # 检查是否存在本地缓存
            if os.path.exists(model_cache_path):
                logger.info(f"🔍 发现本地缓存: {model_cache_path}")
                # 查找实际的模型目录
                snapshots_dir = os.path.join(model_cache_path, "snapshots")
                if os.path.exists(snapshots_dir):
                    # 找到第一个snapshot目录
                    snapshots = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
                    if snapshots:
                        actual_model_path = os.path.join(snapshots_dir, snapshots[0])
                        logger.info(f"🎯 使用缓存模型路径: {actual_model_path}")
                        model_name = actual_model_path
            
            self.model = BGEM3FlagModel(
                model_name_or_path=model_name,
                device=device,
                use_fp16=True if 'cuda' in device else False  # GPU 使用半精度加速
            )
            self.dimensions = 1024  # BGE-M3 固定为 1024 维
            
            logger.success(f"✅ BGE-M3 模型加载成功！向量维度: {self.dimensions}")
            if 'cuda' in device:
                logger.info(f"   🚀 GPU 加速已启用（设备: {device}）")
        else:
            # 使用 sentence-transformers
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "sentence-transformers 模型需要 sentence-transformers 库。请运行: pip install sentence-transformers"
                )
            logger.info("🔧 使用 sentence-transformers 模型")
            logger.info(f"   设备: {device}")
            logger.info("⏳ 首次运行需要下载模型，请稍候...")
            
            self.model = SentenceTransformer(model_name, device=device)
            self.dimensions = self.model.get_sentence_embedding_dimension()
            
            logger.success(f"✅ 本地模型加载成功！向量维度: {self.dimensions}")
            if 'cuda' in device:
                logger.info(f"   🚀 GPU 加速已启用（设备: {device}）")
    
    def embed_text(self, text: str) -> List[float]:
        """
        单文本 embedding（兼容 GeminiEmbeddingClient 接口）
        
        Args:
            text: 输入文本
            
        Returns:
            向量
        """
        return self.embed_query(text)
    
    def embed_query(self, text: str) -> List[float]:
        """
        单文本 embedding
        
        Args:
            text: 输入文本
            
        Returns:
            向量
        """
        if self.use_bge_m3:
            # BGE-M3 使用 encode 方法，返回 dense embeddings
            embeddings = self.model.encode([text], return_dense=True)
            vector = embeddings['dense_vecs'][0]
            return vector.tolist()
        else:
            # sentence-transformers
            vector = self.model.encode(text, show_progress_bar=False)
            return vector.tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量 embedding
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        return self.embed_batch(texts, batch_size=32)
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        max_workers: int = 1,  # 本地模型不需要并发，保持接口兼容
        request_delay: float = 0.0  # 本地模型不需要延迟，保持接口兼容
    ) -> List[List[float]]:
        """
        批量处理
        
        Args:
            texts: 文本列表
            batch_size: 批次大小（GPU 可以设置更大，如 64 或 128）
            max_workers: 并发数（本地模型不使用，保持接口兼容）
            request_delay: 延迟时间（本地模型不使用，保持接口兼容）
            
        Returns:
            向量列表
        """
        logger.info(f"📦 批量 embedding: {len(texts)} 个文本，批次大小: {batch_size}")
        
        if self.use_bge_m3:
            # BGE-M3 批量处理
            all_vectors = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                embeddings = self.model.encode(batch, return_dense=True)
                vectors = embeddings['dense_vecs']
                all_vectors.extend([v.tolist() for v in vectors])
            
            logger.success(f"✅ 批量 embedding 完成: {len(all_vectors)} 个向量")
            return all_vectors
        else:
            # sentence-transformers 批量处理
            all_vectors = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                vectors = self.model.encode(
                    batch,
                    show_progress_bar=False,
                    batch_size=batch_size
                )
                all_vectors.extend([v.tolist() for v in vectors])
            
            logger.success(f"✅ 批量 embedding 完成: {len(all_vectors)} 个向量")
            return all_vectors
    
    def embed_chunks(
        self,
        chunks: List[dict],
        text_key: str = 'text',
        batch_size: int = 32,
        max_workers: int = 1,  # 本地模型不需要并发，保持接口兼容
        request_delay: float = 0.0  # 本地模型不需要延迟，保持接口兼容
    ) -> List[dict]:
        """
        Chunks embedding
        
        Args:
            chunks: chunk 列表
            text_key: 文本字段名
            batch_size: 批次大小（GPU 可以设置更大，如 64 或 128）
            max_workers: 并发数（本地模型不使用，保持接口兼容）
            request_delay: 延迟时间（本地模型不使用，保持接口兼容）
            
        Returns:
            添加了 vector 字段的 chunks
        """
        logger.info(f"📚 开始对 {len(chunks)} 个 chunks 进行 embedding")
        
        # 提取文本
        texts = [chunk[text_key] for chunk in chunks]
        
        # 批量 embedding
        vectors = self.embed_batch(texts, batch_size=batch_size, max_workers=max_workers, request_delay=request_delay)
        
        # 添加向量到 chunks
        embedded_chunks = []
        for chunk, vector in zip(chunks, vectors):
            embedded_chunk = chunk.copy()
            embedded_chunk['vector'] = vector
            embedded_chunks.append(embedded_chunk)
        
        logger.success(f"✅ Chunks embedding 完成: {len(embedded_chunks)} 个")
        
        return embedded_chunks


if __name__ == "__main__":
    # 测试本地 Embedding
    print("\n" + "="*60)
    print("测试本地 Embedding 模型")
    print("="*60)
    
    # 测试 BGE-M3 模型（如果可用）
    if FLAG_EMBEDDING_AVAILABLE:
        print("\n【测试 BGE-M3 模型】")
        try:
            client_bge = LocalEmbeddingClient(model_name="BAAI/bge-m3")
            
            # 测试中文
            print("\n测试1: 中文文本")
            text_cn = "德国联邦议院是德国的最高立法机构。"
            vector_cn = client_bge.embed_query(text_cn)
            print(f"文本: {text_cn}")
            print(f"向量维度: {len(vector_cn)}")
            print(f"向量前5维: {vector_cn[:5]}")
            
            # 测试德语
            print("\n测试2: 德语文本")
            text_de = "Der Deutsche Bundestag ist das Parlament der Bundesrepublik Deutschland."
            vector_de = client_bge.embed_query(text_de)
            print(f"文本: {text_de}")
            print(f"向量维度: {len(vector_de)}")
            print(f"向量前5维: {vector_de[:5]}")
            
            # 测试批量
            print("\n测试3: 批量 embedding")
            texts = [
                "社民党是德国历史最悠久的政党之一。",
                "基民盟在德国政治中扮演重要角色。",
                "绿党关注环境和气候问题。"
            ]
            vectors = client_bge.embed_batch(texts, batch_size=2)
            print(f"批量处理: {len(texts)} 个文本 -> {len(vectors)} 个向量")
            
            print("\n✅ BGE-M3 测试完成！")
        except Exception as e:
            print(f"\n❌ BGE-M3 测试失败: {e}")
    
    # 测试 sentence-transformers 模型（如果可用）
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        print("\n【测试 sentence-transformers 模型】")
        try:
            client_st = LocalEmbeddingClient(model_name="paraphrase-multilingual-MiniLM-L12-v2")
            
            # 测试中文
            print("\n测试1: 中文文本")
            text_cn = "德国联邦议院是德国的最高立法机构。"
            vector_cn = client_st.embed_query(text_cn)
            print(f"文本: {text_cn}")
            print(f"向量维度: {len(vector_cn)}")
            print(f"向量前5维: {vector_cn[:5]}")
            
            print("\n✅ sentence-transformers 测试完成！")
        except Exception as e:
            print(f"\n❌ sentence-transformers 测试失败: {e}")
    
    print("\n✅ 所有测试完成！")
