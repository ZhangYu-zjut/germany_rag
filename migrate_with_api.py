#!/usr/bin/env python3
"""
使用云端API的德国议会数据迁移脚本
临时解决方案，绕过GPU模型加载问题
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import argparse
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.utils.logger import setup_logger
from src.vectordb.qdrant_client import create_qdrant_client
from src.llm.embeddings import GeminiEmbeddingClient
from src.data_loader.splitter import ParliamentTextSplitter

logger = setup_logger()

class CloudAPIMigrator:
    """使用云端API的迁移器"""
    
    def __init__(self, collection_name: str = "german_parliament"):
        self.collection_name = collection_name
        
        # 设置保守参数
        self.embedding_batch_size = 50
        self.qdrant_batch_size = 25
        
        logger.info("🔗 初始化Qdrant客户端...")
        os.environ["QDRANT_MODE"] = "local"
        os.environ["QDRANT_LOCAL_PATH"] = "./data/qdrant"
        self.qdrant_client = create_qdrant_client()
        
        logger.info("🌐 初始化云端embedding客户端...")
        # 使用云端API而不是本地GPU模型
        self.embedding_client = GeminiEmbeddingClient(
            api_key=os.getenv("GEMINI_API_KEY"),
            embedding_mode="api"  # 使用API模式
        )
        
        logger.info("🧠 初始化文本分割器...")
        self.text_splitter = ParliamentTextSplitter(
            chunk_size=512,
            chunk_overlap=50
        )
    
    def migrate_single_year(self, year: int, data_file: Path) -> bool:
        """迁移单个年份的数据（云端API版）"""
        
        logger.info(f"🚀 开始迁移{year}年数据: {data_file}")
        start_time = time.time()
        
        try:
            # 检查集合是否存在
            logger.info(f"[{year}] 📋 确保Qdrant集合存在...")
            self.qdrant_client.create_collection_for_german_parliament(self.collection_name)
            
            # 读取JSON数据
            logger.info(f"[{year}] 📖 读取数据文件...")
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            transcript = data.get('transcript', [])
            logger.info(f"[{year}] 📊 原始记录数: {len(transcript)}")
            
            if not transcript:
                logger.warning(f"[{year}] ⚠️  无数据，跳过")
                return True
            
            # 文本分块
            logger.info(f"[{year}] ✂️  文本分块处理...")
            all_chunks = []
            valid_records = 0
            
            for i, record in enumerate(transcript):
                if not isinstance(record, dict):
                    continue
                
                speech_text = record.get('speech', '').strip()
                if not speech_text or len(speech_text) < 10:
                    continue
                
                valid_records += 1
                
                # 分块
                chunks = self.text_splitter.split_text(speech_text)
                
                # 构建元数据
                metadata = record.get('metadata', {})
                base_metadata = {
                    "year": metadata.get('year', year),
                    "month": metadata.get('month', ''),
                    "day": metadata.get('day', ''),
                    "speaker": metadata.get('speaker', ''),
                    "party": metadata.get('party', ''),
                    "text_id": metadata.get('id', f"{year}_{i}")
                }
                
                # 为每个chunk创建条目
                for j, chunk in enumerate(chunks):
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": j,
                        "total_chunks": len(chunks)
                    })
                    
                    all_chunks.append({
                        "text": chunk,
                        "metadata": chunk_metadata
                    })
            
            logger.info(f"[{year}] 📊 有效记录: {valid_records}, 总chunks: {len(all_chunks)}")
            
            # 分批处理
            total_chunks = len(all_chunks)
            processed = 0
            
            for i in range(0, total_chunks, self.embedding_batch_size):
                batch_chunks = all_chunks[i:i + self.embedding_batch_size]
                batch_num = i // self.embedding_batch_size + 1
                
                logger.info(f"[{year}] 🌐 处理批次 {batch_num}, 大小: {len(batch_chunks)}")
                
                # 生成embedding (使用云端API)
                try:
                    chunks_with_embeddings = self.embedding_client.embed_chunks(
                        batch_chunks,
                        text_key="text",
                        batch_size=self.embedding_batch_size,
                        max_workers=3,  # 降低并发数
                        request_delay=2.0  # 增加延迟避免API限制
                    )
                    logger.info(f"[{year}] ✅ 批次 {batch_num} embedding完成")
                except Exception as e:
                    logger.error(f"[{year}] ❌ 批次 {batch_num} embedding失败: {str(e)}")
                    continue
                
                # 准备Qdrant数据点
                points_to_upsert = []
                point_id = int(time.time() * 1000000) + i
                
                for chunk_data in chunks_with_embeddings:
                    vector = chunk_data.get("vector")
                    if vector is None or len(vector) == 0:
                        continue
                    
                    # 验证向量
                    if any(not isinstance(x, (int, float)) or x != x for x in vector):
                        continue
                    
                    payload = chunk_data.get("metadata", {})
                    payload["text"] = chunk_data.get("text", "")
                    
                    points_to_upsert.append({
                        "id": point_id,
                        "vector": vector,
                        "payload": payload
                    })
                    point_id += 1
                
                # 批量插入到Qdrant
                if points_to_upsert:
                    try:
                        self.qdrant_client.upsert_german_parliament_data(
                            collection_name=self.collection_name,
                            data_points=points_to_upsert
                        )
                        logger.info(f"[{year}] ✅ 批次 {batch_num} Qdrant插入完成")
                    except Exception as e:
                        logger.error(f"[{year}] ❌ 批次 {batch_num} Qdrant插入失败: {str(e)}")
                        continue
                
                processed += len(batch_chunks)
                progress = (processed / total_chunks) * 100
                logger.info(f"[{year}] 📊 进度: {progress:.1f}% ({processed}/{total_chunks})")
                
                # 避免API限制
                time.sleep(1)
            
            duration = time.time() - start_time
            logger.info(f"[{year}] ✅ 迁移完成: {processed}个chunks, 耗时: {duration:.1f}秒")
            return True
            
        except Exception as e:
            logger.error(f"[{year}] ❌ 迁移失败: {str(e)}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="云端API德国议会数据迁移脚本")
    parser.add_argument("--year", type=int, required=True, help="要迁移的年份")
    parser.add_argument("--data-dir", type=str, default="./data/pp_json_49-21", help="数据目录")
    
    args = parser.parse_args()
    
    logger.info("🌐 启动云端API迁移脚本")
    logger.info(f"   目标年份: {args.year}")
    logger.info(f"   数据目录: {args.data_dir}")
    
    # 检查API密钥
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("❌ GEMINI_API_KEY环境变量未设置")
        return False
    
    # 查找数据文件
    data_dir = Path(args.data_dir)
    
    if args.year == 2021:
        data_file = data_dir / "pp_2021_merged.json"
        if not data_file.exists():
            data_file = data_dir / "pp_2021.json"
    else:
        data_file = data_dir / f"pp_{args.year}.json"
    
    if not data_file.exists():
        logger.error(f"❌ 数据文件不存在: {data_file}")
        return False
    
    # 开始迁移
    migrator = CloudAPIMigrator()
    success = migrator.migrate_single_year(args.year, data_file)
    
    if success:
        logger.info(f"🎉 {args.year}年数据迁移成功完成！")
        return True
    else:
        logger.error(f"❌ {args.year}年数据迁移失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
