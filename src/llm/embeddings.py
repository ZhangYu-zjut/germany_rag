"""
Embedding客户端模块
封装Gemini Embedding的调用
支持多种模式：local（本地BGE-M3）、openai、deepinfra、vertex
"""

from langchain_openai import OpenAIEmbeddings
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import requests
import json
from src.config import settings
from src.utils import logger

# 延迟导入 LocalEmbeddingClient，避免循环导入
_local_client = None


def _get_local_client():
    """延迟导入 LocalEmbeddingClient"""
    global _local_client
    if _local_client is None:
        from src.llm.local_embeddings import LocalEmbeddingClient
        _local_client = LocalEmbeddingClient
    return _local_client


class GeminiEmbeddingClient:
    """
    Gemini Embedding客户端
    
    功能:
    1. 文本向量化(Embedding)
    2. 批量Embedding
    3. 支持中文和德语
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        dimensions: Optional[int] = None,
        embedding_mode: Optional[str] = None
    ):
        """
        初始化Embedding客户端
        
        Args:
            model_name: Embedding模型名称,默认从配置读取
            dimensions: 向量维度,默认从配置读取
            embedding_mode: Embedding模式（"openai", "deepinfra", "local", "vertex"），默认从配置读取
        """
        # 从配置读取embedding模式
        self.embedding_mode = embedding_mode or settings.embedding_mode
        
        # 根据模式选择配置
        if self.embedding_mode == "local":
            # 本地模式：使用 LocalEmbeddingClient
            self.model_name = model_name or settings.local_embedding_model
            self.dimensions = dimensions or settings.local_embedding_dimension
            logger.info("✅ 使用本地 Embedding 模型（完全免费，支持 GPU 加速）")
            
            # 导入并初始化本地客户端
            LocalEmbeddingClient = _get_local_client()
            self.local_client = LocalEmbeddingClient(model_name=self.model_name)
            self.dimensions = self.local_client.dimensions  # 从实际模型获取维度
            self.embeddings = None
            self.api_key = None
            self.api_url = None
            
        elif self.embedding_mode == "deepinfra":
            self.model_name = model_name or settings.deepinfra_embedding_model
            self.dimensions = dimensions or settings.deepinfra_embedding_dimension
            api_key = settings.deepinfra_embedding_api_key
            base_url = settings.deepinfra_embedding_base_url
            logger.info("✅ 使用DeepInfra Embedding API（速度更快、价格更便宜）")
        elif self.embedding_mode == "openai":
            self.model_name = model_name or settings.openai_embedding_model
            self.dimensions = dimensions or settings.openai_embedding_dimension
            api_key = settings.openai_embedding_api_key
            base_url = settings.openai_embedding_base_url
            logger.info("✅ 使用OpenAI官方API")
        else:
            # 其他模式暂不支持，使用OpenAI作为fallback
            logger.warning(f"⚠️  不支持的embedding模式: {self.embedding_mode}，使用OpenAI作为fallback")
            self.model_name = model_name or settings.openai_embedding_model
            self.dimensions = dimensions or settings.openai_embedding_dimension
            api_key = settings.openai_embedding_api_key
            base_url = settings.openai_embedding_base_url
        
        # 根据模式记录日志
        if self.embedding_mode == "local":
            logger.info(
                f"初始化Embedding客户端: mode={self.embedding_mode}, "
                f"model={self.model_name}, dimensions={self.dimensions}"
            )
        else:
            logger.info(
                f"初始化Embedding客户端: mode={self.embedding_mode}, "
                f"model={self.model_name}, dimensions={self.dimensions}, base_url={base_url}"
            )
        
        try:
            # 本地模式已在上面初始化，跳过
            if self.embedding_mode == "local":
                logger.success("✅ Embedding客户端初始化成功")
            # DeepInfra使用requests直接调用（模拟curl）
            elif self.embedding_mode == "deepinfra":
                self.api_key = api_key
                self.api_url = f"{base_url.rstrip('/')}/embeddings"
                self.embeddings = None  # 不使用LangChain包装器
                logger.info("🔧 DeepInfra使用requests直接调用（模拟curl）")
                logger.info(f"   API URL: {self.api_url}")
                logger.success("✅ Embedding客户端初始化成功")
            else:
                # 其他模式使用LangChain包装器
                embeddings_kwargs = {
                    "model": self.model_name,
                    "api_key": api_key,
                    "base_url": base_url
                }
                
                if self.embedding_mode == "openai" and self.dimensions:
                    embeddings_kwargs["dimensions"] = self.dimensions
                
                self.embeddings = OpenAIEmbeddings(**embeddings_kwargs)
                self.api_key = None
                self.api_url = None
                logger.success("✅ Embedding客户端初始化成功")
            
        except Exception as e:
            logger.error(f"❌ Embedding客户端初始化失败: {e}")
            logger.warning("⚠️  请检查:")
            if self.embedding_mode == "local":
                logger.warning("  1. FlagEmbedding 或 sentence-transformers 是否正确安装")
                logger.warning("  2. 模型名称是否正确")
                logger.warning("  3. GPU 是否可用（如果使用 GPU）")
            else:
                logger.warning("  1. API Key是否正确")
                logger.warning("  2. base_url是否支持embedding接口")
                logger.warning("  3. 模型名称是否正确")
                if self.embedding_mode == "deepinfra":
                    logger.warning("  4. 确保.env文件中配置了DEEPINFRA_EMBEDDING_API_KEY和DEEPINFRA_EMBEDDING_BASE_URL")
            raise
    
    def _call_deepinfra_api(self, input_data) -> dict:
        """
        使用requests调用DeepInfra API（模拟curl）
        
        Args:
            input_data: 输入数据（字符串或字符串列表）
        
        Returns:
            API响应的JSON数据
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "input": input_data,
            "model": self.model_name,
            "encoding_format": "float"
        }
        
        logger.debug(f"DeepInfra API调用: {len(input_data) if isinstance(input_data, list) else 1}个输入")
        
        response = requests.post(
            self.api_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=60  # 60秒超时
        )
        
        if response.status_code != 200:
            raise Exception(f"API调用失败: HTTP {response.status_code} - {response.text}")
        
        return response.json()

    def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行向量化
        
        Args:
            text: 输入文本
        
        Returns:
            文本的向量表示(list of floats)
        """
        try:
            if self.embedding_mode == "local":
                # 本地模式使用 LocalEmbeddingClient
                vector = self.local_client.embed_text(text)
            elif self.embedding_mode == "deepinfra":  # DeepInfra使用requests
                response_data = self._call_deepinfra_api(text)
                vector = response_data["data"][0]["embedding"]
            else:  # 其他模式使用LangChain
                vector = self.embeddings.embed_query(text)
            
            logger.debug(
                f"文本embedding成功: 文本长度={len(text)}, "
                f"向量维度={len(vector)}"
            )
            
            return vector
            
        except Exception as e:
            logger.error(f"文本embedding失败: {e}")
            raise
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 800,  # 🚀 GPU显存优化：充分利用16GB显存，性能提升13x
        max_workers: int = 20,   # 提高并发数到20，大幅提升速度
        max_retries: int = 5,   # 增加重试次数
        request_delay: float = 0.5  # 🚀 优化：减少延迟，提高吞吐量
    ) -> List[List[float]]:
        """
        批量文本向量化（优化版本：支持大批次和并发）

        Args:
            texts: 文本列表
            batch_size: 批次大小（默认100，平衡速度和稳定性）
            max_workers: 并发线程数（默认20，大幅提升处理速度）
            max_retries: 最大重试次数（默认5）
            request_delay: 批次间延迟时间（秒，默认1秒），避免触发速率限制

        Returns:
            向量列表,每个向量对应一个文本
        """
        try:
            # 🔧 重要修复：本地GPU模型不支持并发，强制使用单线程
            if self.embedding_mode == "local":
                max_workers = 1
                logger.warning("⚠️  本地GPU模式检测到，自动禁用并发（max_workers=1）以避免GPU资源竞争")

            total = len(texts)
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(
                f"开始批量Embedding（优化版）: {total}个文本，"
                f"批次大小: {batch_size}，并发数: {max_workers}，"
                f"批次间延迟: {request_delay}s，预计{total_batches}批"
            )
            
            # 使用tqdm显示进度
            try:
                from tqdm import tqdm
                use_tqdm = True
            except ImportError:
                use_tqdm = False
            
            # 准备批次索引
            batch_indices = list(range(0, total, batch_size))
            
            # 用于存储结果（按顺序）
            results = [None] * len(batch_indices)
            
            def process_batch(batch_idx: int, batch_num: int) -> tuple:
                """处理单个批次（带重试机制）"""
                start_idx = batch_idx
                end_idx = min(start_idx + batch_size, total)
                batch = texts[start_idx:end_idx]
                
                # 添加批次间延迟，避免触发速率限制
                # batch_num从1开始，第一个批次不延迟
                if batch_num > 1 and request_delay > 0:
                    time.sleep(request_delay)
                
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        # 根据模式调用不同的embedding方法
                        if self.embedding_mode == "local":
                            # 本地模式：直接调用，无需重试（本地不会出现网络错误）
                            vectors = self.local_client.embed_batch(batch, batch_size=len(batch))
                            return batch_num, vectors
                        elif self.embedding_mode == "deepinfra":  # DeepInfra使用requests
                            response_data = self._call_deepinfra_api(batch)
                            vectors = [data["embedding"] for data in response_data["data"]]
                        else:  # 其他模式使用LangChain
                            vectors = self.embeddings.embed_documents(batch)
                        
                        return batch_num, vectors
                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e).lower()
                        
                        # 检查是否是速率限制或连接错误
                        is_rate_limit = "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg
                        is_connection_error = "connection" in error_msg or "ssl" in error_msg or "eof" in error_msg
                        
                        if is_rate_limit or is_connection_error:
                            # 更长的指数退避：5秒 -> 10秒 -> 20秒 ...
                            wait_time = min(5 * (2 ** (retry_count - 1)), 60)
                            error_type = "速率限制" if is_rate_limit else "连接错误"
                            logger.warning(
                                f"批次 {batch_num} 遇到{error_type}，"
                                f"等待 {wait_time} 秒后重试 ({retry_count}/{max_retries})"
                            )
                            time.sleep(wait_time)
                        elif "quota" in error_msg or "quota exceeded" in error_msg:
                            # 配额错误需要更长的等待时间
                            wait_time = min(15 * retry_count, 120)
                            logger.warning(
                                f"批次 {batch_num} 遇到配额限制，"
                                f"等待 {wait_time} 秒后重试 ({retry_count}/{max_retries})"
                            )
                            time.sleep(wait_time)
                        else:
                            # 非速率限制错误，直接抛出
                            logger.error(f"批次 {batch_num} 处理失败: {e}")
                            raise
                
                # 所有重试都失败
                raise Exception(f"批次 {batch_num} 处理失败：已达到最大重试次数 {max_retries}")
            
            # 使用并发处理
            start_time = time.time()
            completed = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_batch = {
                    executor.submit(process_batch, idx, i + 1): (idx, i + 1)
                    for i, idx in enumerate(batch_indices)
                }
                
                # 使用tqdm显示进度
                if use_tqdm:
                    pbar = tqdm(total=total_batches, desc="生成Embedding", unit="批")
                
                # 收集结果
                for future in as_completed(future_to_batch):
                    batch_idx, batch_num = future_to_batch[future]
                    try:
                        result_batch_num, vectors = future.result()
                        batch_list_idx = batch_indices.index(batch_idx)
                        results[batch_list_idx] = vectors
                        completed += 1
                        
                        if use_tqdm:
                            pbar.update(1)
                        else:
                            logger.info(
                                f"完成批次 {result_batch_num}/{total_batches}: "
                                f"{len(vectors)}个向量 (已完成: {completed}/{total_batches})"
                            )
                    except Exception as e:
                        logger.error(f"批次 {batch_num} 执行失败: {e}")
                        raise
                
                if use_tqdm:
                    pbar.close()
            
            # 合并结果
            all_vectors = []
            for vectors in results:
                if vectors is not None:
                    all_vectors.extend(vectors)
            
            elapsed_time = time.time() - start_time
            throughput = total / elapsed_time if elapsed_time > 0 else 0
            
            logger.success(
                f"批量embedding完成: {total}个文本 -> {len(all_vectors)}个向量，"
                f"耗时: {elapsed_time:.1f}秒，吞吐量: {throughput:.1f}条/秒"
            )
            
            return all_vectors
            
        except Exception as e:
            logger.error(f"批量embedding失败: {e}")
            raise
    
    def embed_chunks(
        self,
        chunks: List[dict],
        text_key: str = 'text',
        batch_size: int = 800,  # 🚀 GPU显存优化：充分利用16GB显存，性能提升13x
        max_workers: int = 20,   # 提高并发数到20，大幅提升速度
        request_delay: float = 0.5  # 🚀 优化：减少延迟，提高吞吐量
    ) -> List[dict]:
        """
        对chunks进行批量embedding
        
        Args:
            chunks: chunk字典列表,每个chunk包含text和metadata
            text_key: 文本字段的key名称
            batch_size: 批次大小
        
        Returns:
            添加了vector字段的chunks列表
        """
        logger.info(f"开始对{len(chunks)}个chunks进行embedding")
        
        # 提取文本
        texts = [chunk[text_key] for chunk in chunks]
        
        # 批量embedding（使用优化版本）
        vectors = self.embed_batch(
            texts, 
            batch_size=batch_size, 
            max_workers=max_workers,
            request_delay=request_delay
        )
        
        # 将向量添加到chunks中
        embedded_chunks = []
        for chunk, vector in zip(chunks, vectors):
            embedded_chunk = chunk.copy()
            embedded_chunk['vector'] = vector
            embedded_chunks.append(embedded_chunk)
        
        logger.success(f"Chunks embedding完成: {len(embedded_chunks)}个")
        
        return embedded_chunks


if __name__ == "__main__":
    # 测试Embedding客户端
    client = GeminiEmbeddingClient()
    
    # 测试1: 单文本embedding
    print("\n=== 测试1: 单文本Embedding ===")
    text = "德国联邦议院是德国的最高立法机构。"
    vector = client.embed_text(text)
    print(f"文本: {text}")
    print(f"向量维度: {len(vector)}")
    print(f"向量前5维: {vector[:5]}")
    
    # 测试2: 批量embedding
    print("\n=== 测试2: 批量Embedding ===")
    texts = [
        "社民党是德国历史最悠久的政党之一。",
        "基民盟在德国政治中扮演重要角色。",
        "绿党关注环境和气候问题。",
        "The German Bundestag is located in Berlin.",
        "Die Grünen setzen sich für Umweltschutz ein."
    ]
    vectors = client.embed_batch(texts, batch_size=2)
    print(f"批量embedding: {len(texts)}个文本 -> {len(vectors)}个向量")
    for i, (text, vector) in enumerate(zip(texts, vectors), 1):
        print(f"\n文本{i}: {text}")
        print(f"  向量维度: {len(vector)}")
        print(f"  向量前3维: {vector[:3]}")
    
    # 测试3: Chunks embedding
    print("\n=== 测试3: Chunks Embedding ===")
    test_chunks = [
        {
            'text': '这是第一个chunk的内容。',
            'metadata': {'id': 1, 'speaker': 'Speaker A'}
        },
        {
            'text': '这是第二个chunk的内容。',
            'metadata': {'id': 2, 'speaker': 'Speaker B'}
        }
    ]
    embedded_chunks = client.embed_chunks(test_chunks)
    print(f"Chunks embedding完成: {len(embedded_chunks)}个")
    for chunk in embedded_chunks:
        print(f"\nChunk ID: {chunk['metadata']['id']}")
        print(f"  文本: {chunk['text']}")
        print(f"  向量维度: {len(chunk['vector'])}")
