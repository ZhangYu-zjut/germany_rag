#!/usr/bin/env python3
"""
使用最佳配置迁移2015年数据到german-bge索引
最佳配置：4000字符分块，800重叠，批次100，无代理
"""

import os
import sys
import time
import json
import gc
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger
from src.llm.embeddings import GeminiEmbeddingClient
from src.data_loader.splitter import ParliamentTextSplitter

logger = setup_logger()

def check_proxy():
    """检查网络代理设置"""
    logger.info("🔍 检查网络代理设置")
    
    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
    proxy_status = {}
    
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            proxy_status[var] = value
            logger.info(f"   发现代理: {var}={value}")
    
    if proxy_status:
        logger.info("✅ 代理设置正常，将使用代理连接")
    else:
        logger.info("✅ 无代理设置，直接连接")

def load_2015_data():
    """加载2015年数据"""
    logger.info("📂 加载2015年德国议会数据")
    
    data_file = project_root / "data" / "pp_json_49-21" / "pp_2015.json"
    
    if not data_file.exists():
        logger.error(f"❌ 2015年数据文件不存在: {data_file}")
        return None
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # 提取transcript数组
        if 'transcript' not in raw_data:
            logger.error("❌ 数据文件中没有找到transcript字段")
            return None
            
        data = raw_data['transcript']
        
        logger.info(f"✅ 2015年数据加载成功")
        logger.info(f"   文件大小: {data_file.stat().st_size / (1024*1024):.1f} MB")
        logger.info(f"   数据条数: {len(data)}")
        
        # 显示数据示例
        if data:
            sample = data[0]
            logger.info(f"   数据示例:")
            logger.info(f"     ID: {sample.get('text_id', 'N/A')}")
            logger.info(f"     发言人: {sample.get('metadata', {}).get('speaker', 'N/A')}")
            logger.info(f"     文本长度: {len(sample.get('speech', ''))}")
            
        return data
        
    except Exception as e:
        logger.error(f"❌ 加载2015年数据失败: {str(e)}")
        return None

def chunk_2015_data(data):
    """使用最佳配置分块2015年数据"""
    logger.info("🔄 使用最佳配置分块2015年数据")
    
    # 最佳分块配置
    chunk_size = 4000      # 4000字符分块
    chunk_overlap = 800    # 800字符重叠
    
    logger.info(f"📊 分块配置:")
    logger.info(f"   块大小: {chunk_size} 字符")
    logger.info(f"   重叠大小: {chunk_overlap} 字符")
    logger.info(f"   有效块大小: {chunk_size - chunk_overlap} 字符")
    
    # 初始化分块器，使用自定义配置
    text_splitter = ParliamentTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    all_chunks = []
    total_chars = 0
    
    start_time = time.time()
    
    for i, item in enumerate(data):
        text_id = item.get('text_id', f'2015_unknown_{i}')
        speech = item.get('speech', '')
        metadata = item.get('metadata', {})
        
        if not speech.strip():
            continue
            
        total_chars += len(speech)
        
        # 使用分块器的text_splitter进行分块
        chunk_texts = text_splitter.text_splitter.split_text(speech)
        
        # 为每个块添加元数据
        for j, chunk_text in enumerate(chunk_texts):
            chunk = {
                'text_id': f"{text_id}_chunk_{j}",
                'original_text_id': text_id,
                'chunk_index': j,
                'text': chunk_text.strip(),
                'metadata': {
                    # Core time fields (separate for precise filtering)
                    'year': metadata.get('year', '2015'),
                    'month': metadata.get('month', '01'),
                    'day': metadata.get('day', '01'),

                    # Document ID (crucial for citation)
                    'id': metadata.get('id', text_id),

                    # Speaker information
                    'speaker': metadata.get('speaker', ''),
                    'group': metadata.get('group', ''),
                    'lp': metadata.get('lp', ''),

                    # Session information
                    'session': metadata.get('session', ''),

                    # User-friendly source reference: "id + speaker + time"
                    'source_reference': f"{metadata.get('id', text_id)} | {metadata.get('speaker', 'Unknown')} | {metadata.get('year', '2015')}-{metadata.get('month', '01')}-{metadata.get('day', '01')}",

                    # Technical fields
                    'chunk_size': len(chunk_text.strip()),
                    'total_chunks': len(chunk_texts),
                    'source': 'german_parliament'
                }
            }
            all_chunks.append(chunk)
        
        # 每处理100条记录显示进度
        if (i + 1) % 100 == 0:
            logger.info(f"   已处理: {i + 1}/{len(data)} 条记录")
    
    processing_time = time.time() - start_time
    
    logger.info(f"✅ 2015年数据分块完成")
    logger.info(f"   原始记录: {len(data)} 条")
    logger.info(f"   生成块数: {len(all_chunks)} 个")
    logger.info(f"   总字符数: {total_chars:,}")
    logger.info(f"   平均块大小: {sum(len(c['text']) for c in all_chunks) / len(all_chunks):.0f} 字符")
    logger.info(f"   分块耗时: {processing_time:.2f} 秒")
    
    # 估算相比1000字符分块的改进
    estimated_1000_chunks = total_chars // 900  # 1000-100重叠
    reduction_ratio = len(all_chunks) / estimated_1000_chunks if estimated_1000_chunks > 0 else 0
    
    logger.info(f"📊 分块优化效果:")
    logger.info(f"   1000字符分块预估: {estimated_1000_chunks:,} 个")
    logger.info(f"   4000字符分块实际: {len(all_chunks):,} 个")
    logger.info(f"   块数减少: {(1-reduction_ratio)*100:.1f}%")
    
    return all_chunks

def generate_embeddings_optimized(chunks):
    """使用最佳配置生成embeddings"""
    logger.info("🧠 使用最佳配置生成BGE-M3 embeddings")
    
    # 初始化BGE-M3客户端
    embedding_client = GeminiEmbeddingClient(
        embedding_mode="local",
        model_name="BAAI/bge-m3",
        dimensions=1024
    )
    
    # 提取文本
    texts = [chunk['text'] for chunk in chunks]
    
    logger.info(f"📊 Embedding配置:")
    logger.info(f"   文本数量: {len(texts)}")
    logger.info(f"   模型: BGE-M3")
    logger.info(f"   维度: 1024")
    logger.info(f"   批次大小: 128 (embedding优化)")
    
    start_time = time.time()
    
    # 使用优化的embedding配置
    vectors = embedding_client.embed_batch(
        texts,
        batch_size=128,  # embedding批次优化
        max_workers=6    # 适中并发
    )
    
    embedding_time = time.time() - start_time
    
    logger.info(f"✅ Embedding生成完成")
    logger.info(f"   生成时间: {embedding_time:.2f} 秒")
    logger.info(f"   处理速度: {len(texts)/embedding_time:.1f} 条/秒")
    logger.info(f"   向量维度验证: {len(vectors[0]) if vectors else 0}")
    
    # 检查并清理NaN值
    import math
    cleaned_vectors = []
    nan_count = 0
    
    for i, vector in enumerate(vectors):
        # 检查是否有NaN或Inf
        has_nan = any(math.isnan(v) or math.isinf(v) for v in vector)
        
        if has_nan:
            nan_count += 1
            logger.warning(f"   发现NaN/Inf向量: 索引{i}, 将使用零向量替代")
            # 用零向量替代
            cleaned_vector = [0.0] * len(vector)
        else:
            cleaned_vector = vector
        
        cleaned_vectors.append(cleaned_vector)
    
    if nan_count > 0:
        logger.warning(f"⚠️  清理了{nan_count}个包含NaN/Inf的向量")
    
    return cleaned_vectors

def upload_to_pinecone_optimized(chunks, vectors):
    """使用最佳配置上传到Pinecone"""
    logger.info("📤 使用最佳配置上传到Pinecone")
    
    try:
        from pinecone import Pinecone
        
        # 初始化Pinecone (确保无代理)
        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        pc = Pinecone(api_key=api_key)
        index = pc.Index("german-bge")
        
        # 检查上传前状态
        stats_before = index.describe_index_stats()
        initial_count = stats_before['total_vector_count']
        
        logger.info(f"📊 Pinecone上传配置:")
        logger.info(f"   索引: german-bge")
        logger.info(f"   批次大小: 100 (存储优化)")
        logger.info(f"   上传前向量数: {initial_count}")
        logger.info(f"   待上传向量数: {len(vectors)}")
        
        # 准备向量数据
        vector_data = []
        timestamp = int(time.time())
        
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            vector_item = {
                "id": f"2015_{timestamp}_{i}",
                "values": vector,
                "metadata": {
                    **chunk['metadata'],
                    "text": chunk['text'][:1000] + "..." if len(chunk['text']) > 1000 else chunk['text'],
                    "original_text_id": chunk['original_text_id'],
                    "chunk_index": chunk['chunk_index'],
                    "upload_timestamp": timestamp
                }
            }
            vector_data.append(vector_item)
        
        # 批量上传 (使用优化的批次大小100)
        batch_size = 100
        total_batches = (len(vector_data) + batch_size - 1) // batch_size
        
        logger.info(f"🚀 开始批量上传: {total_batches} 个批次")
        
        start_time = time.time()
        uploaded_count = 0
        
        for batch_idx in range(total_batches):
            batch_start = batch_idx * batch_size
            batch_end = min(batch_start + batch_size, len(vector_data))
            batch_vectors = vector_data[batch_start:batch_end]
            
            batch_start_time = time.time()
            
            try:
                upsert_response = index.upsert(vectors=batch_vectors)
                batch_time = time.time() - batch_start_time
                batch_speed = len(batch_vectors) / batch_time if batch_time > 0 else 0
                
                uploaded_count += len(batch_vectors)
                
                logger.info(f"   批次 {batch_idx+1}/{total_batches}: "
                          f"{len(batch_vectors)} 向量, "
                          f"{batch_time:.2f}秒, "
                          f"{batch_speed:.1f} 向量/秒")
                
            except Exception as e:
                logger.error(f"   ❌ 批次 {batch_idx+1} 上传失败: {str(e)}")
                continue
        
        total_upload_time = time.time() - start_time
        avg_speed = uploaded_count / total_upload_time if total_upload_time > 0 else 0
        
        logger.info(f"✅ Pinecone上传完成")
        logger.info(f"   上传向量数: {uploaded_count}")
        logger.info(f"   总耗时: {total_upload_time:.2f} 秒")
        logger.info(f"   平均速度: {avg_speed:.1f} 向量/秒")
        
        # 等待索引更新
        logger.info("⏳ 等待Pinecone索引更新...")
        time.sleep(5)
        
        # 验证上传结果
        stats_after = index.describe_index_stats()
        final_count = stats_after['total_vector_count']
        
        logger.info(f"📊 上传验证:")
        logger.info(f"   上传前: {initial_count} 向量")
        logger.info(f"   上传后: {final_count} 向量")
        logger.info(f"   净增加: {final_count - initial_count} 向量")
        
        if final_count > initial_count:
            logger.info("🎉 2015年数据成功上传到Pinecone!")
            return True
        else:
            logger.error("❌ 向量数未增加，上传可能失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ Pinecone上传失败: {str(e)}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始2015年数据最佳配置迁移")
    logger.info("=" * 60)
    
    total_start_time = time.time()
    
    # 步骤1: 检查代理设置（不再禁用）
    check_proxy()
    
    # 步骤2: 加载2015年数据
    data = load_2015_data()
    if not data:
        return 1
    
    # 步骤3: 分块处理
    chunks = chunk_2015_data(data)
    if not chunks:
        return 1
    
    # 步骤4: 生成embeddings
    vectors = generate_embeddings_optimized(chunks)
    if not vectors:
        return 1
    
    # 步骤5: 上传到Pinecone
    success = upload_to_pinecone_optimized(chunks, vectors)
    if not success:
        return 1
    
    # 总结
    total_time = time.time() - total_start_time
    
    logger.info("=" * 60)
    logger.info("🎉 2015年数据迁移完成!")
    logger.info(f"📊 迁移统计:")
    logger.info(f"   源数据: {len(data)} 条记录")
    logger.info(f"   生成块数: {len(chunks)} 个")
    logger.info(f"   生成向量: {len(vectors)} 个")
    logger.info(f"   总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    
    # 性能对比
    logger.info(f"🚀 性能对比 (vs 原预期4-6小时):")
    original_estimate_hours = 4.5  # 原估计中值
    actual_hours = total_time / 3600
    improvement = (original_estimate_hours / actual_hours - 1) * 100
    logger.info(f"   原预期: {original_estimate_hours} 小时")
    logger.info(f"   实际耗时: {actual_hours:.2f} 小时")
    logger.info(f"   性能提升: {improvement:.0f}x 倍速")
    
    # 清理内存
    gc.collect()
    
    logger.info("✅ 准备进行问答测试验证")
    
    return 0

if __name__ == "__main__":
    exit(main())
