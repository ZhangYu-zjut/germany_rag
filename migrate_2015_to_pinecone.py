#!/usr/bin/env python3
"""
2015年数据迁移到Pinecone german-bge index
使用BGE-M3模型 (1024维)
Chunk配置: size=4000, overlap=800
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
from tqdm import tqdm

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger
from src.data_loader.splitter import ParliamentTextSplitter

logger = setup_logger()

@dataclass
class ProcessingStats:
    """数据处理统计"""
    total_records: int = 0
    total_chunks: int = 0
    total_vectors: int = 0
    processing_time: float = 0
    embedding_time: float = 0
    upload_time: float = 0

    def print_summary(self):
        """打印统计摘要"""
        logger.info("\n" + "="*60)
        logger.info("📊 2015年数据处理统计")
        logger.info("="*60)
        logger.info(f"总记录数: {self.total_records}")
        logger.info(f"生成Chunks: {self.total_chunks}")
        logger.info(f"生成向量数: {self.total_vectors}")
        logger.info(f"数据处理时间: {self.processing_time:.2f}秒")
        logger.info(f"Embedding时间: {self.embedding_time:.2f}秒")
        logger.info(f"上传时间: {self.upload_time:.2f}秒")
        logger.info(f"总耗时: {self.processing_time + self.embedding_time + self.upload_time:.2f}秒")
        logger.info("="*60)

class Migrate2015ToPinecone:
    """2015年数据迁移到Pinecone"""

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 800):
        """初始化迁移系统"""
        logger.info("🚀 初始化2015年数据迁移到Pinecone")
        logger.info(f"📝 Chunk配置: size={chunk_size}, overlap={chunk_overlap}")

        # Pinecone配置
        self.pinecone_api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        self.pinecone_host = os.getenv("PINECONE_HOST")

        if not self.pinecone_api_key:
            raise ValueError("❌ PINECONE_VECTOR_DATABASE_API_KEY 环境变量未设置")
        if not self.pinecone_host:
            raise ValueError("❌ PINECONE_HOST 环境变量未设置")

        # 初始化文本分块器
        self.text_splitter = ParliamentTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Pinecone客户端
        self.pc = None
        self.index = None
        self.index_name = "german-bge"

        # 统计信息
        self.stats = ProcessingStats()

        logger.info("✅ 迁移系统初始化完成")

    def init_pinecone(self):
        """初始化Pinecone连接"""
        logger.info("🔗 连接Pinecone...")

        try:
            from pinecone import Pinecone

            self.pc = Pinecone(api_key=self.pinecone_api_key)

            # 连接到german-bge index
            self.index = self.pc.Index(self.index_name, host=self.pinecone_host)

            # 获取index统计信息
            stats = self.index.describe_index_stats()
            logger.info(f"✅ 成功连接到index: {self.index_name}")
            logger.info(f"📊 当前index统计: {stats}")

            return True

        except Exception as e:
            logger.error(f"❌ Pinecone连接失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def load_2015_data(self) -> List[Dict]:
        """加载2015年数据"""
        logger.info("📂 加载2015年数据...")

        data_file = Path("data/pp_json_49-21/pp_2015.json")

        if not data_file.exists():
            raise FileNotFoundError(f"❌ 数据文件不存在: {data_file}")

        start_time = time.time()

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        transcripts = data.get('transcript', [])

        # 过滤有效记录（有speaker和speech内容）
        valid_records = []
        for record in transcripts:
            metadata = record.get('metadata', {})
            speech = record.get('speech', '')

            if speech and speech.strip():
                valid_records.append({
                    'metadata': metadata,
                    'speech': speech
                })

        load_time = time.time() - start_time

        logger.info(f"✅ 加载完成: {len(transcripts)}条原始记录")
        logger.info(f"✅ 有效记录: {len(valid_records)}条")
        logger.info(f"⏱️  加载耗时: {load_time:.2f}秒")

        self.stats.total_records = len(valid_records)

        return valid_records

    def process_data_to_chunks(self, records: List[Dict]) -> List[Dict]:
        """将数据处理成chunks"""
        logger.info("✂️  开始文本分块...")

        start_time = time.time()

        # 使用text_splitter处理
        chunks = self.text_splitter.split_speeches(records)

        process_time = time.time() - start_time
        self.stats.processing_time = process_time
        self.stats.total_chunks = len(chunks)

        logger.info(f"✅ 分块完成: {len(chunks)}个chunks")
        logger.info(f"⏱️  处理耗时: {process_time:.2f}秒")

        return chunks

    def create_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """生成embeddings"""
        logger.info("🧮 开始生成embeddings...")
        logger.info("📝 使用BGE-M3本地模型 (1024维)")

        start_time = time.time()

        try:
            # 使用本地BGE-M3模型
            from FlagEmbedding import BGEM3FlagModel

            logger.info("📥 加载BGE-M3模型...")
            model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
            logger.info("✅ 模型加载成功")

            # 批量生成embeddings
            batch_size = 16
            embedded_chunks = []

            for i in tqdm(range(0, len(chunks), batch_size), desc="生成embeddings"):
                batch = chunks[i:i+batch_size]
                texts = [chunk['text'] for chunk in batch]

                # 生成embeddings
                embeddings = model.encode(texts, batch_size=batch_size)['dense_vecs']

                # 添加到结果
                for j, chunk in enumerate(batch):
                    embedded_chunk = chunk.copy()
                    embedded_chunk['values'] = embeddings[j].tolist()
                    embedded_chunks.append(embedded_chunk)

            embed_time = time.time() - start_time
            self.stats.embedding_time = embed_time
            self.stats.total_vectors = len(embedded_chunks)

            logger.info(f"✅ Embeddings生成完成: {len(embedded_chunks)}个向量")
            logger.info(f"⏱️  Embedding耗时: {embed_time:.2f}秒")

            return embedded_chunks

        except Exception as e:
            logger.error(f"❌ Embedding生成失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def upload_to_pinecone(self, embedded_chunks: List[Dict]):
        """上传向量到Pinecone"""
        logger.info("📤 开始上传到Pinecone...")

        start_time = time.time()

        try:
            batch_size = 100
            total_uploaded = 0

            for i in tqdm(range(0, len(embedded_chunks), batch_size), desc="上传向量"):
                batch = embedded_chunks[i:i+batch_size]

                # 准备upsert数据
                vectors = []
                for chunk in batch:
                    metadata = chunk['metadata']
                    vector_id = f"2015_{metadata.get('id', f'chunk_{i}')}"

                    vectors.append({
                        'id': vector_id,
                        'values': chunk['values'],
                        'metadata': {
                            'year': str(metadata.get('year', '2015')),
                            'month': str(metadata.get('month', '')),
                            'day': str(metadata.get('day', '')),
                            'speaker': str(metadata.get('speaker', '')),
                            'group': str(metadata.get('group', '')),
                            'text': chunk['text'][:1000],  # 限制文本长度
                            'session': str(metadata.get('session', '')),
                            'lp': str(metadata.get('lp', ''))
                        }
                    })

                # 上传到Pinecone
                self.index.upsert(vectors=vectors)
                total_uploaded += len(vectors)

            upload_time = time.time() - start_time
            self.stats.upload_time = upload_time

            logger.info(f"✅ 上传完成: {total_uploaded}个向量")
            logger.info(f"⏱️  上传耗时: {upload_time:.2f}秒")

        except Exception as e:
            logger.error(f"❌ 上传失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def run(self):
        """执行完整迁移流程"""
        logger.info("\n" + "="*60)
        logger.info("🚀 开始2015年数据迁移")
        logger.info("="*60 + "\n")

        try:
            # 1. 连接Pinecone
            if not self.init_pinecone():
                return False

            # 2. 加载数据
            records = self.load_2015_data()

            # 3. 数据分块
            chunks = self.process_data_to_chunks(records)

            # 4. 生成embeddings
            embedded_chunks = self.create_embeddings(chunks)

            # 5. 上传到Pinecone
            self.upload_to_pinecone(embedded_chunks)

            # 6. 打印统计信息
            self.stats.print_summary()

            logger.info("\n✅ 2015年数据迁移成功完成！")

            return True

        except Exception as e:
            logger.error(f"\n❌ 迁移过程失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def main():
    """主函数"""
    migrator = Migrate2015ToPinecone(chunk_size=4000, chunk_overlap=800)
    success = migrator.run()

    if success:
        logger.info("\n🎉 迁移成功完成!")
        return 0
    else:
        logger.error("\n❌ 迁移失败")
        return 1

if __name__ == "__main__":
    exit(main())
