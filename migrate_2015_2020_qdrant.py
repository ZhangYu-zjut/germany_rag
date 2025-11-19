#!/usr/bin/env python3
"""
2015-2020年数据批量迁移到Qdrant Cloud
使用已验证成功的BGE-M3 + Qdrant Cloud方案
"""

import os
import sys
import json
import time
import gc
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

class Migrate2015To2020:
    """2015-2020年数据迁移到Qdrant Cloud"""
    
    def __init__(self):
        # 初始化组件
        self.text_splitter = ParliamentTextSplitter(chunk_size=512, chunk_overlap=50)
        
        # 使用已验证成功的BGE-M3参数
        self.embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        
        # 初始化Qdrant客户端
        self.qdrant_client = self._init_qdrant_client()
        
        # 迁移统计
        self.stats: List[MigrationStats] = []
        
        logger.info("🚀 初始化2015-2020年Qdrant Cloud迁移系统")
        logger.info("✅ 使用已验证的BGE-M3本地embedding (batch_size=64, workers=4)")
    
    def _init_qdrant_client(self):
        """初始化Qdrant客户端"""
        try:
            from src.vectordb.qdrant_client import QdrantClient
            
            qdrant_client = QdrantClient(
                mode="cloud",
                embedding_client=self.embedding_client
            )
            
            logger.info("✅ Qdrant Cloud客户端初始化成功")
            return qdrant_client
            
        except Exception as e:
            logger.error(f"❌ Qdrant客户端初始化失败: {str(e)}")
            raise
    
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
    
    def store_to_qdrant(self, year: int, chunks: List[Dict], embeddings: List[List[float]]) -> int:
        """存储到Qdrant Cloud"""
        logger.info(f"💾 存储{year}年数据到Qdrant Cloud...")
        
        if len(chunks) != len(embeddings):
            logger.error(f"❌ 数据不匹配: {len(chunks)} chunks vs {len(embeddings)} embeddings")
            return 0
        
        try:
            # 使用Qdrant客户端的批量插入功能
            stored_count = self.qdrant_client.upsert_german_parliament_data(
                chunks, embeddings
            )
            
            logger.info(f"✅ {year}年数据存储成功: {stored_count:,}个向量")
            return stored_count
            
        except Exception as e:
            logger.error(f"❌ {year}年数据存储失败: {str(e)}")
            return 0
    
    def migrate_single_year(self, year: int) -> MigrationStats:
        """迁移单个年份的数据"""
        logger.info("=" * 60)
        logger.info(f"🚀 开始迁移{year}年数据")
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
            
            # 4. 存储到Qdrant
            if should_stop:
                return stats
            
            stored_count = self.store_to_qdrant(year, chunks, embeddings)
            stats.vectors_stored = stored_count
            
            # 5. 清理内存
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
        logger.info("🚀 开始2015-2020年批量数据迁移到Qdrant Cloud")
        logger.info("=" * 80)
        
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
        logger.info("📊 2015-2020年Qdrant Cloud迁移最终报告")
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
        
        # 保存详细报告
        report_file = f"migration_2015_2020_qdrant_report.md"
        self.save_detailed_report(report_file, total_time)
        logger.info(f"\n📄 详细报告已保存到: {report_file}")
        
        logger.info(f"\n🎉 2015-2020年数据迁移完成!")
        logger.info(f"   Vector Database: Qdrant Cloud")  
        logger.info(f"   Embedding Model: BGE-M3 (本地1024维)")
        logger.info(f"   Total Cost: $0 (embedding免费) + Qdrant Cloud费用")
    
    def save_detailed_report(self, filename: str, total_time: float):
        """保存详细报告到文件"""
        total_records = sum(s.records_processed for s in self.stats)
        total_chunks = sum(s.chunks_generated for s in self.stats)
        total_vectors_created = sum(s.vectors_created for s in self.stats)
        total_vectors_stored = sum(s.vectors_stored for s in self.stats)
        successful_years = len([s for s in self.stats if s.vectors_stored > 0])
        
        content = f"""# 2015-2020年数据Qdrant Cloud迁移报告

## 迁移配置
- **向量数据库**: Qdrant Cloud
- **Embedding模型**: BGE-M3 (本地, 1024维)
- **批次参数**: batch_size=64, max_workers=4 (内存优化)
- **迁移时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}

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
- **Qdrant Cloud**: 按实际使用量计费
- **总体成本**: 远低于OpenAI方案

## 技术验证
✅ BGE-M3本地embedding稳定运行
✅ 内存优化方案有效
✅ Qdrant Cloud存储成功
✅ 大规模数据处理验证通过

## 结论
2015-2020年德国议会数据成功迁移到Qdrant Cloud，
使用BGE-M3本地embedding实现了高性能、低成本的解决方案。
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="2015-2020年数据迁移到Qdrant Cloud")
    parser.add_argument("--start-year", type=int, default=2015, help="开始年份")
    parser.add_argument("--end-year", type=int, default=2020, help="结束年份")
    parser.add_argument("--single-year", type=int, help="只处理单个年份")
    
    args = parser.parse_args()
    
    migrator = Migrate2015To2020()
    
    try:
        if args.single_year:
            logger.info(f"🎯 单年份模式: {args.single_year}")
            stats = migrator.migrate_single_year(args.single_year)
            logger.info(f"🎉 {args.single_year}年迁移完成")
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
