#!/usr/bin/env python3
"""
批量迁移2016-2025年数据到Pinecone
基于已验证的migrate_2015_optimal_config.py配置
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
from pinecone import Pinecone

logger = setup_logger()


def migrate_year(year: int, embedding_client, text_splitter, pinecone_index, skip_if_exists=True):
    """
    迁移单个年份的数据

    Args:
        year: 年份
        embedding_client: Embedding客户端
        text_splitter: 文本分块器
        pinecone_index: Pinecone索引
        skip_if_exists: 如果数据已存在则跳过

    Returns:
        dict: 迁移结果统计
    """
    logger.info("="*80)
    logger.info(f"🚀 开始迁移 {year} 年数据")
    logger.info("="*80)

    start_time = time.time()

    try:
        # 1. 检查是否已迁移
        if skip_if_exists:
            stats = pinecone_index.describe_index_stats()
            # 检查是否有该年份的数据
            query_result = pinecone_index.query(
                vector=[0.0] * 1024,
                filter={"year": {"$eq": str(year)}},
                top_k=1,
                include_metadata=False
            )
            if query_result.matches:
                logger.info(f"⏭️  {year}年数据已存在，跳过")
                return {
                    "year": year,
                    "status": "skipped",
                    "reason": "already_exists"
                }

        # 2. 加载数据
        data_file = project_root / "data" / "pp_json_49-21" / f"pp_{year}.json"

        if not data_file.exists():
            logger.warning(f"⚠️  {year}年数据文件不存在: {data_file}")
            return {
                "year": year,
                "status": "failed",
                "reason": "file_not_found"
            }

        logger.info(f"📂 加载{year}年数据文件...")
        with open(data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        if 'transcript' not in raw_data:
            logger.error(f"❌ {year}年数据文件格式错误")
            return {
                "year": year,
                "status": "failed",
                "reason": "invalid_format"
            }

        data = raw_data['transcript']
        file_size_mb = data_file.stat().st_size / (1024*1024)

        logger.info(f"✅ {year}年数据加载成功")
        logger.info(f"   文件大小: {file_size_mb:.1f} MB")
        logger.info(f"   数据条数: {len(data)}")

        # 3. 分块处理
        logger.info(f"🔄 分块{year}年数据...")
        all_chunks = []
        total_chars = 0

        for i, item in enumerate(data):
            text_id = item.get('text_id', f'{year}_unknown_{i}')
            speech = item.get('speech', '')
            metadata = item.get('metadata', {})

            if not speech.strip():
                continue

            total_chars += len(speech)

            # 分块
            chunk_texts = text_splitter.text_splitter.split_text(speech)

            # 添加元数据
            for j, chunk_text in enumerate(chunk_texts):
                chunk = {
                    'text_id': f"{text_id}_chunk_{j}",
                    'original_text_id': text_id,
                    'chunk_index': j,
                    'text': chunk_text.strip(),
                    'metadata': {
                        # Core time fields (separate for precise filtering)
                        'year': metadata.get('year', str(year)),
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
                        'source_reference': f"{metadata.get('id', text_id)} | {metadata.get('speaker', 'Unknown')} | {metadata.get('year', year)}-{metadata.get('month', '01')}-{metadata.get('day', '01')}",

                        # Technical fields
                        'chunk_size': len(chunk_text.strip()),
                        'total_chunks': len(chunk_texts),
                        'source': 'german_parliament'
                    }
                }
                all_chunks.append(chunk)

        logger.info(f"✅ {year}年数据分块完成")
        logger.info(f"   原始记录: {len(data)} 条")
        logger.info(f"   生成块数: {len(all_chunks)} 个")
        logger.info(f"   平均块大小: {sum(len(c['text']) for c in all_chunks) / len(all_chunks):.0f} 字符")

        # 4. 生成Embeddings
        logger.info(f"🧠 生成{year}年BGE-M3 embeddings...")
        texts = [chunk['text'] for chunk in all_chunks]

        embedding_start = time.time()
        vectors = embedding_client.embed_batch(
            texts,
            batch_size=128,  # embedding优化
            max_workers=1    # GPU单线程
        )
        embedding_time = time.time() - embedding_start

        logger.info(f"✅ Embedding生成完成")
        logger.info(f"   生成时间: {embedding_time:.2f} 秒")
        logger.info(f"   处理速度: {len(texts)/embedding_time:.1f} 条/秒")

        # 检查NaN
        import math
        nan_count = sum(1 for v in vectors if any(math.isnan(x) or math.isinf(x) for x in v))
        if nan_count > 0:
            logger.error(f"❌ 发现{nan_count}个NaN/Inf向量")
            return {
                "year": year,
                "status": "failed",
                "reason": "nan_vectors"
            }

        # 5. 上传到Pinecone
        logger.info(f"📤 上传{year}年数据到Pinecone...")

        # 获取上传前状态
        stats_before = pinecone_index.describe_index_stats()
        initial_count = stats_before['total_vector_count']

        # 准备向量数据
        vector_data = []
        timestamp = int(time.time())

        for i, (chunk, vector) in enumerate(zip(all_chunks, vectors)):
            vector_item = {
                "id": f"{year}_{timestamp}_{i}",
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

        # 批量上传
        batch_size = 100
        total_batches = (len(vector_data) + batch_size - 1) // batch_size

        upload_start = time.time()
        uploaded_count = 0

        for batch_idx in range(total_batches):
            batch_start = batch_idx * batch_size
            batch_end = min(batch_start + batch_size, len(vector_data))
            batch_vectors = vector_data[batch_start:batch_end]

            try:
                pinecone_index.upsert(vectors=batch_vectors)
                uploaded_count += len(batch_vectors)

                if (batch_idx + 1) % 10 == 0:
                    logger.info(f"   进度: {batch_idx+1}/{total_batches} 批次")
            except Exception as e:
                logger.error(f"   ❌ 批次 {batch_idx+1} 上传失败: {str(e)}")
                continue

        upload_time = time.time() - upload_start

        logger.info(f"✅ Pinecone上传完成")
        logger.info(f"   上传向量数: {uploaded_count}")
        logger.info(f"   上传时间: {upload_time:.2f} 秒")
        logger.info(f"   平均速度: {uploaded_count/upload_time:.1f} 向量/秒")

        # 等待索引更新
        time.sleep(3)

        # 验证
        stats_after = pinecone_index.describe_index_stats()
        final_count = stats_after['total_vector_count']

        logger.info(f"📊 上传验证:")
        logger.info(f"   上传前: {initial_count} 向量")
        logger.info(f"   上传后: {final_count} 向量")
        logger.info(f"   净增加: {final_count - initial_count} 向量")

        total_time = time.time() - start_time

        logger.info(f"🎉 {year}年数据迁移完成!")
        logger.info(f"   总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")

        # 保存统计信息（在删除变量之前）
        records_count = len(data)
        chunks_count = len(all_chunks)

        # 清理内存
        del vectors, vector_data, all_chunks, data
        gc.collect()

        return {
            "year": year,
            "status": "success",
            "records": records_count,
            "chunks": chunks_count,
            "vectors": uploaded_count,
            "embedding_time": embedding_time,
            "upload_time": upload_time,
            "total_time": total_time
        }

    except Exception as e:
        logger.error(f"❌ {year}年数据迁移失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            "year": year,
            "status": "failed",
            "reason": str(e)
        }


def main():
    """主函数"""
    logger.info("🚀 开始2016-2025年数据批量迁移")
    logger.info("="*80)

    total_start = time.time()

    # 初始化
    logger.info("🔧 初始化系统组件...")

    # Embedding客户端
    embedding_client = GeminiEmbeddingClient(
        embedding_mode="local",
        model_name="BAAI/bge-m3",
        dimensions=1024
    )
    logger.info("✅ BGE-M3 Embedding客户端初始化完成")

    # Pinecone
    api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
    pc = Pinecone(api_key=api_key)
    index = pc.Index("german-bge")
    logger.info("✅ Pinecone客户端初始化完成")

    # 文本分块器
    text_splitter = ParliamentTextSplitter(
        chunk_size=4000,
        chunk_overlap=800
    )
    logger.info("✅ 文本分块器初始化完成 (4000/800)")

    # 检查初始状态
    stats_initial = index.describe_index_stats()
    logger.info(f"📊 迁移前Pinecone状态: {stats_initial['total_vector_count']} 向量")

    # 要迁移的年份 (2015已完成，从2016开始)
    years = list(range(2016, 2026))  # 2016-2025

    logger.info(f"📋 计划迁移年份: {years}")
    logger.info(f"   共{len(years)}个年份")

    results = []

    # 逐年迁移
    for i, year in enumerate(years, 1):
        logger.info(f"\n\n{'='*80}")
        logger.info(f"📅 处理第 {i}/{len(years)} 个年份: {year}")
        logger.info(f"{'='*80}\n")

        result = migrate_year(
            year=year,
            embedding_client=embedding_client,
            text_splitter=text_splitter,
            pinecone_index=index,
            skip_if_exists=True
        )

        results.append(result)

        # 保存进度
        progress_file = project_root / "batch_migration_progress_2016_2025.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 进度已保存到 {progress_file}")

    # 总结
    total_time = time.time() - total_start

    logger.info("\n\n" + "="*80)
    logger.info("🎉 批量迁移完成!")
    logger.info("="*80)

    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')

    logger.info(f"\n📊 迁移统计:")
    logger.info(f"   成功: {success_count}")
    logger.info(f"   失败: {failed_count}")
    logger.info(f"   跳过: {skipped_count}")
    logger.info(f"   总耗时: {total_time/60:.1f} 分钟")

    # 详细结果
    logger.info(f"\n📋 详细结果:")
    for result in results:
        year = result['year']
        status = result['status']

        if status == 'success':
            logger.info(f"   ✅ {year}: {result['vectors']} 向量, {result['total_time']/60:.1f} 分钟")
        elif status == 'failed':
            logger.info(f"   ❌ {year}: 失败 - {result.get('reason', 'unknown')}")
        elif status == 'skipped':
            logger.info(f"   ⏭️  {year}: 跳过 - {result.get('reason', 'unknown')}")

    # 最终Pinecone状态
    stats_final = index.describe_index_stats()
    logger.info(f"\n📊 迁移后Pinecone状态:")
    logger.info(f"   总向量数: {stats_final['total_vector_count']}")
    logger.info(f"   净增加: {stats_final['total_vector_count'] - stats_initial['total_vector_count']}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit(main())
