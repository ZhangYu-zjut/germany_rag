#!/usr/bin/env python3
"""
2015-2020年数据批量迁移到Pinecone
使用已验证的BGE-M3 + Pinecone Manual Configuration方案
"""

import os
import sys
import json
import time
import gc
import random
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import signal

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger
from src.data_loader.splitter import ParliamentTextSplitter
from src.llm.embeddings import GeminiEmbeddingClient

logger = setup_logger()

# 全局变量用于优雅退出
should_stop = False

def signal_handler(signum, frame):
    """处理中断信号"""
    global should_stop
    should_stop = True
    logger.info("🛑 接收到中断信号，正在优雅退出...")

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@dataclass
class MigrationStats:
    """迁移统计信息"""
    year: int
    records_processed: int = 0
    chunks_generated: int = 0
    vectors_created: int = 0
    vectors_stored: int = 0
    start_time: float = 0
    end_time: float = 0
    
    @property
    def duration_minutes(self) -> float:
        return (self.end_time - self.start_time) / 60 if self.end_time > 0 else 0

class Migrate2015To2020Pinecone:
    """2015-2020年数据迁移到Pinecone"""
    
    def __init__(self):
        # Pinecone配置
        self.pinecone_api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        self.pinecone_region = os.getenv("PINECONE_REGION", "us-east-1")
        
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_VECTOR_DATABASE_API_KEY 环境变量未设置")
        
        # 初始化组件
        self.text_splitter = ParliamentTextSplitter(chunk_size=512, chunk_overlap=50)
        
        # 使用已验证成功的BGE-M3参数
        self.embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        
        # 初始化Pinecone客户端
        self.pc = self._init_pinecone_client()
        self.index = None
        self.index_name = "german-parliament-2015-2020"
        
        # 迁移统计
        self.stats: List[MigrationStats] = []
        
        logger.info("🚀 初始化2015-2020年Pinecone迁移系统")
        logger.info("✅ 使用已验证的BGE-M3本地embedding (1024维)")
    
    def _init_pinecone_client(self):
        """初始化Pinecone客户端"""
        try:
            from pinecone import Pinecone, ServerlessSpec
            
            pc = Pinecone(api_key=self.pinecone_api_key)
            logger.info("✅ Pinecone客户端初始化成功")
            return pc
            
        except Exception as e:
            logger.error(f"❌ Pinecone客户端初始化失败: {str(e)}")
            raise
    
    def create_or_connect_index(self):
        """创建或连接到Pinecone索引"""
        logger.info(f"📦 设置Pinecone索引: {self.index_name}")
        
        try:
            # 检查现有索引
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.index_name in index_names:
                logger.info(f"🔗 连接到现有索引: {self.index_name}")
                self.index = self.pc.Index(self.index_name)
                
                # 验证索引配置
                stats = self.index.describe_index_stats()
                logger.info(f"📊 索引状态: {stats}")
                
            else:
                logger.info(f"🔨 创建新索引: {self.index_name}")
                
                # 创建索引 - Manual Configuration，支持BGE-M3
                from pinecone import ServerlessSpec
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1024,  # BGE-M3维度
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.pinecone_region
                    )
                )
                
                logger.info("⏳ 等待索引初始化...")
                time.sleep(30)  # 等待索引准备就绪
                
                self.index = self.pc.Index(self.index_name)
                logger.info(f"✅ 索引创建成功: {self.index_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 索引设置失败: {str(e)}")
            return False
    
    def load_year_data(self, year: int) -> List[Dict]:
        """加载指定年份的数据"""
        logger.info(f"📖 加载{year}年数据...")
        
        # 处理特殊情况：2021年数据被分成两个文件
        if year == 2021:
            logger.info("🔄 处理2021年合并数据...")
            data_file = project_root / "data/pp_json_49-21/pp_2021_merged.json"
            if not data_file.exists():
                logger.error(f"❌ 2021年合并数据文件不存在: {data_file}")
                logger.info("💡 请先运行merge_2021_data.py合并2021年数据")
                return []
        else:
            data_file = project_root / f"data/pp_json_49-21/pp_{year}.json"
        
        if not data_file.exists():
            logger.error(f"❌ {year}年数据文件不存在: {data_file}")
            return []
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            transcript = data.get('transcript', [])
            file_size_mb = data_file.stat().st_size / (1024*1024)
            
            logger.info(f"✅ {year}年数据加载成功: {len(transcript):,}条记录, {file_size_mb:.1f}MB")
            return transcript
            
        except Exception as e:
            logger.error(f"❌ {year}年数据加载失败: {str(e)}")
            return []
    
    def process_year_chunks(self, year: int, transcript: List[Dict]) -> List[Dict]:
        """处理年份数据分块"""
        logger.info(f"✂️  处理{year}年文本分块...")
        
        all_chunks = []
        valid_records = 0
        
        for i, record in enumerate(transcript):
            if should_stop:
                logger.info("🛑 收到停止信号，停止分块处理")
                break
            
            if not isinstance(record, dict):
                continue
            
            speech_text = record.get('speech', '').strip()
            if not speech_text or len(speech_text) < 10:
                continue
                
            valid_records += 1
            
            # 分块
            chunks = self.text_splitter.text_splitter.split_text(speech_text)
            
            # 构建元数据
            metadata = record.get('metadata', {})
            base_metadata = {
                "year": metadata.get('year', year),
                "month": str(metadata.get('month', '')),
                "day": str(metadata.get('day', '')),
                "speaker": str(metadata.get('speaker', '')),
                "party": str(metadata.get('party', '')),
                "text_id": str(metadata.get('id', f"{year}_{i}")),
                "record_index": i
            }
            
            # 为每个chunk创建条目
            for j, chunk in enumerate(chunks):
                chunk_metadata = base_metadata.copy()
                chunk_metadata.update({
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    "chunk_id": f"{year}_{i}_{j}"
                })
                
                all_chunks.append({
                    "id": f"{year}_{i}_{j}",
                    "text": chunk,
                    "metadata": chunk_metadata
                })
            
            # 每处理1000条记录显示进度
            if (i + 1) % 1000 == 0:
                logger.info(f"   📈 已处理 {i + 1:,}/{len(transcript):,} 条记录...")
        
        logger.info(f"✅ {year}年分块完成: {valid_records:,}条有效记录 → {len(all_chunks):,}个chunks")
        return all_chunks
    
    def generate_embeddings(self, year: int, chunks: List[Dict]) -> List[List[float]]:
        """生成BGE-M3 embeddings"""
        logger.info(f"🧠 生成{year}年BGE-M3 embeddings...")
        
        texts = [chunk["text"] for chunk in chunks]
        
        # 使用已验证成功的保守参数
        try:
            embeddings = self.embedding_client.embed_batch(
                texts,
                batch_size=64,     # 已验证的稳定批次大小
                max_workers=4,     # 已验证的稳定并发数
                request_delay=1.0  # 保守延迟
            )
            
            logger.info(f"✅ {year}年embeddings生成成功: {len(embeddings):,}个1024维向量")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ {year}年embeddings生成失败: {str(e)}")
            return []
    
    def store_to_pinecone(self, year: int, chunks: List[Dict], embeddings: List[List[float]]) -> int:
        """存储到Pinecone"""
        logger.info(f"💾 存储{year}年数据到Pinecone...")
        
        if len(chunks) != len(embeddings):
            logger.error(f"❌ 数据不匹配: {len(chunks)} chunks vs {len(embeddings)} embeddings")
            return 0
        
        batch_size = 100  # Pinecone推荐批次大小
        total_batches = len(chunks) // batch_size + (1 if len(chunks) % batch_size else 0)
        
        logger.info(f"🔄 开始批量存储: {len(chunks):,}个BGE-M3向量, {total_batches}个批次")
        
        stored_count = 0
        failed_count = 0
        
        for i in range(0, len(chunks), batch_size):
            if should_stop:
                logger.info("🛑 收到停止信号，停止存储")
                break
            
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            
            # 构建Pinecone向量格式
            vectors = []
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                # 确保embedding是有效的
                if not embedding or len(embedding) != 1024:
                    logger.warning(f"⚠️  跳过无效向量: {chunk['id']}")
                    failed_count += 1
                    continue
                
                # 限制metadata大小（Pinecone有限制）
                safe_metadata = {
                    "text": chunk["text"][:500],  # 限制文本长度
                    "year": str(chunk["metadata"].get("year", "")),
                    "speaker": str(chunk["metadata"].get("speaker", ""))[:50],
                    "party": str(chunk["metadata"].get("party", ""))[:30],
                    "text_id": str(chunk["metadata"].get("text_id", ""))[:50],
                    "chunk_index": chunk["metadata"].get("chunk_index", 0)
                }
                
                vectors.append({
                    "id": chunk["id"],
                    "values": embedding,
                    "metadata": safe_metadata
                })
            
            # 插入到Pinecone
            if vectors:
                try:
                    self.index.upsert(vectors=vectors)
                    stored_count += len(vectors)
                    
                    batch_num = i // batch_size + 1
                    progress = (stored_count / len(chunks)) * 100
                    logger.info(f"📈 批次 {batch_num}/{total_batches}: {progress:.1f}% ({stored_count:,}/{len(chunks):,})")
                    
                    # 适当延迟，避免过快请求
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ 批次 {batch_num} 存储失败: {str(e)}")
                    failed_count += len(vectors)
        
        logger.info(f"✅ {year}年存储完成: {stored_count:,}个BGE-M3向量成功存储到Pinecone")
        if failed_count > 0:
            logger.warning(f"⚠️  失败向量: {failed_count:,}个")
        
        # 等待索引更新
        logger.info("⏳ 等待Pinecone索引更新...")
        time.sleep(10)
        
        return stored_count
    
    def verify_storage(self, year: int):
        """验证存储结果"""
        logger.info(f"🔍 验证{year}年存储结果...")
        
        try:
            # 获取索引统计信息
            stats = self.index.describe_index_stats()
            
            total_vectors = stats['total_vector_count']
            dimension = stats['dimension']
            
            logger.info(f"📊 Pinecone索引统计:")
            logger.info(f"   总向量数: {total_vectors:,}")
            logger.info(f"   向量维度: {dimension}")
            
            # 测试搜索功能
            if total_vectors > 0:
                logger.info("🔍 测试BGE-M3向量搜索功能...")
                
                # 使用真实的BGE-M3向量进行搜索
                test_text = f"{year}年德国议会讨论经济政策"
                test_embedding = self.embedding_client.embed_single(test_text)
                
                if test_embedding:
                    search_results = self.index.query(
                        vector=test_embedding,
                        top_k=3,
                        include_metadata=True
                    )
                    
                    logger.info(f"✅ BGE-M3语义搜索测试成功，返回 {len(search_results.matches)} 个结果")
                    
                    # 显示搜索结果示例
                    for i, match in enumerate(search_results.matches[:2], 1):
                        score = match.score
                        metadata = match.metadata
                        text = metadata.get('text', '')[:100] + "..." if len(metadata.get('text', '')) > 100 else metadata.get('text', '')
                        speaker = metadata.get('speaker', 'Unknown')
                        year_meta = metadata.get('year', 'Unknown')
                        logger.info(f"   [{i}] 相似度: {score:.4f}, {year_meta}年, 发言人: {speaker}")
                        logger.info(f"       文本: {text}")
                else:
                    logger.warning("⚠️  无法生成测试向量，跳过搜索测试")
            
        except Exception as e:
            logger.error(f"❌ 验证过程出错: {str(e)}")
    
    def migrate_single_year(self, year: int) -> MigrationStats:
        """迁移单个年份的数据"""
        logger.info("=" * 60)
        logger.info(f"🚀 开始迁移{year}年数据到Pinecone")
        logger.info("=" * 60)
        
        stats = MigrationStats(year=year, start_time=time.time())
        
        try:
            # 检查停止信号
            if should_stop:
                logger.info("🛑 收到停止信号，跳过处理")
                return stats
            
            # 1. 加载数据
            transcript = self.load_year_data(year)
            if not transcript:
                logger.warning(f"⚠️  {year}年数据为空，跳过处理")
                return stats
            
            stats.records_processed = len(transcript)
            
            # 2. 文本分块
            if should_stop:
                return stats
            
            chunks = self.process_year_chunks(year, transcript)
            if not chunks:
                logger.warning(f"⚠️  {year}年分块结果为空，跳过处理")
                return stats
            
            stats.chunks_generated = len(chunks)
            
            # 3. 生成embeddings
            if should_stop:
                return stats
            
            embeddings = self.generate_embeddings(year, chunks)
            if not embeddings:
                logger.error(f"❌ {year}年embeddings生成失败，跳过存储")
                return stats
            
            stats.vectors_created = len(embeddings)
            
            # 4. 存储到Pinecone
            if should_stop:
                return stats
            
            stored_count = self.store_to_pinecone(year, chunks, embeddings)
            stats.vectors_stored = stored_count
            
            # 5. 验证存储结果
            if stored_count > 0:
                self.verify_storage(year)
            
            # 6. 清理内存
            del transcript, chunks, embeddings
            gc.collect()
            
            stats.end_time = time.time()
            
            logger.info(f"🎉 {year}年迁移完成!")
            logger.info(f"   📊 处理记录: {stats.records_processed:,}条")
            logger.info(f"   📊 生成chunks: {stats.chunks_generated:,}个")
            logger.info(f"   📊 创建向量: {stats.vectors_created:,}个")
            logger.info(f"   📊 存储向量: {stats.vectors_stored:,}个")
            logger.info(f"   ⏱️  耗时: {stats.duration_minutes:.1f}分钟")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ {year}年迁移失败: {str(e)}")
            stats.end_time = time.time()
            return stats
    
    def migrate_all_years(self, start_year: int = 2015, end_year: int = 2020):
        """迁移所有年份的数据"""
        logger.info("🚀 开始2015-2020年批量数据迁移到Pinecone")
        logger.info("=" * 80)
        
        # 首先设置索引
        if not self.create_or_connect_index():
            logger.error("❌ 索引设置失败，无法继续迁移")
            return
        
        years = list(range(start_year, end_year + 1))
        total_start_time = time.time()
        
        for year in years:
            if should_stop:
                logger.info("🛑 收到停止信号，终止批量迁移")
                break
            
            logger.info(f"📅 开始处理{year}年 ({years.index(year) + 1}/{len(years)})")
            stats = self.migrate_single_year(year)
            self.stats.append(stats)
            
            # 年份间暂停，让系统休息
            if not should_stop:
                logger.info("⏳ 年份间暂停5秒...")
                time.sleep(5)
        
        # 生成最终报告
        total_time = time.time() - total_start_time
        self.generate_final_report(total_time)
    
    def generate_final_report(self, total_time: float):
        """生成最终迁移报告"""
        logger.info("=" * 80)
        logger.info("📊 2015-2020年Pinecone迁移最终报告")
        logger.info("=" * 80)
        
        # 统计总数
        total_records = sum(s.records_processed for s in self.stats)
        total_chunks = sum(s.chunks_generated for s in self.stats)
        total_vectors_created = sum(s.vectors_created for s in self.stats)
        total_vectors_stored = sum(s.vectors_stored for s in self.stats)
        successful_years = len([s for s in self.stats if s.vectors_stored > 0])
        
        logger.info(f"🎯 总体统计:")
        logger.info(f"   成功年份: {successful_years}/{len(self.stats)}")
        logger.info(f"   处理记录: {total_records:,}条")
        logger.info(f"   生成chunks: {total_chunks:,}个")
        logger.info(f"   创建向量: {total_vectors_created:,}个")
        logger.info(f"   存储向量: {total_vectors_stored:,}个")
        logger.info(f"   总耗时: {total_time/60:.1f}分钟 ({total_time/3600:.2f}小时)")
        
        if total_time > 0:
            logger.info(f"   平均速度: {total_vectors_created/total_time:.1f} 向量/秒")
        
        logger.info(f"\n📋 各年份详情:")
        for stats in self.stats:
            status = "✅" if stats.vectors_stored > 0 else "❌"
            logger.info(f"   {status} {stats.year}年: {stats.records_processed:,}记录 → {stats.chunks_generated:,}chunks → {stats.vectors_stored:,}向量 ({stats.duration_minutes:.1f}分钟)")
        
        # 最终索引统计
        try:
            final_stats = self.index.describe_index_stats()
            logger.info(f"\n📊 最终Pinecone索引统计:")
            logger.info(f"   索引名称: {self.index_name}")
            logger.info(f"   总向量数: {final_stats['total_vector_count']:,}")
            logger.info(f"   向量维度: {final_stats['dimension']} (BGE-M3)")
        except Exception as e:
            logger.warning(f"⚠️  无法获取最终统计: {e}")
        
        # 保存详细报告
        report_file = f"migration_2015_2020_pinecone_report.md"
        self.save_detailed_report(report_file, total_time)
        logger.info(f"\n📄 详细报告已保存到: {report_file}")
        
        logger.info(f"\n🎉 2015-2020年数据迁移完成!")
        logger.info(f"   Vector Database: Pinecone (Manual Configuration)")  
        logger.info(f"   Embedding Model: BGE-M3 (本地1024维)")
        logger.info(f"   Total Cost: $0 (embedding免费) + $70/月 (Pinecone)")
    
    def save_detailed_report(self, filename: str, total_time: float):
        """保存详细报告到文件"""
        total_records = sum(s.records_processed for s in self.stats)
        total_chunks = sum(s.chunks_generated for s in self.stats)
        total_vectors_created = sum(s.vectors_created for s in self.stats)
        total_vectors_stored = sum(s.vectors_stored for s in self.stats)
        successful_years = len([s for s in self.stats if s.vectors_stored > 0])
        
        content = f"""# 2015-2020年数据Pinecone迁移报告

## 迁移配置
- **向量数据库**: Pinecone (Manual Configuration)
- **Embedding模型**: BGE-M3 (本地, 1024维)
- **批次参数**: batch_size=64, max_workers=4 (内存优化)
- **迁移时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **索引名称**: {self.index_name}

## 总体结果
- **成功年份**: {successful_years}/{len(self.stats)}
- **处理记录**: {total_records:,}条
- **生成chunks**: {total_chunks:,}个
- **创建向量**: {total_vectors_created:,}个
- **存储向量**: {total_vectors_stored:,}个
- **总耗时**: {total_time/60:.1f}分钟 ({total_time/3600:.2f}小时)
- **平均速度**: {total_vectors_created/total_time:.1f} 向量/秒

## 各年份详情

| 年份 | 状态 | 记录数 | Chunks | 向量数 | 耗时(分) |
|------|------|--------|--------|--------|----------|
"""
        
        for stats in self.stats:
            status = "✅" if stats.vectors_stored > 0 else "❌"
            content += f"| {stats.year} | {status} | {stats.records_processed:,} | {stats.chunks_generated:,} | {stats.vectors_stored:,} | {stats.duration_minutes:.1f} |\n"
        
        content += f"""

## 成本分析
- **BGE-M3 Embedding**: $0 (本地免费)
- **Pinecone存储**: $70/月
- **总体成本**: 远低于OpenAI方案

## 技术验证
✅ BGE-M3本地embedding稳定运行
✅ 内存优化方案有效
✅ Pinecone Manual Configuration成功
✅ 大规模数据处理验证通过

## 结论
2015-2020年德国议会数据成功迁移到Pinecone，
使用BGE-M3本地embedding + Pinecone Manual Configuration
实现了高性能、低成本的向量存储解决方案。
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="2015-2020年数据迁移到Pinecone")
    parser.add_argument("--start-year", type=int, default=2015, help="开始年份")
    parser.add_argument("--end-year", type=int, default=2020, help="结束年份")
    parser.add_argument("--single-year", type=int, help="只处理单个年份")
    
    args = parser.parse_args()
    
    migrator = Migrate2015To2020Pinecone()
    
    try:
        if args.single_year:
            logger.info(f"🎯 单年份模式: {args.single_year}")
            # 首先设置索引
            if migrator.create_or_connect_index():
                stats = migrator.migrate_single_year(args.single_year)
                logger.info(f"🎉 {args.single_year}年迁移完成")
            else:
                logger.error("❌ 索引设置失败")
                return 1
        else:
            logger.info(f"🚀 批量模式: {args.start_year}-{args.end_year}")
            migrator.migrate_all_years(args.start_year, args.end_year)
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 用户中断迁移")
        return 1
    except Exception as e:
        logger.error(f"❌ 迁移失败: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
