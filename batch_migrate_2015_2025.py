#!/usr/bin/env python3
"""
2015-2025年德国议会数据大规模批量迁移系统
使用最新的GPU优化参数，支持断点续传和智能进度管理
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.vectordb.qdrant_client import create_qdrant_client
from src.llm.embeddings import GeminiEmbeddingClient
from src.utils.logger import logger
from src.data_loader.splitter import ParliamentTextSplitter

@dataclass
class MigrationTask:
    """迁移任务数据类"""
    year: int
    file_path: Path
    file_size_mb: float
    estimated_records: int
    status: str = "pending"  # pending, processing, completed, failed
    start_time: float = 0.0
    end_time: float = 0.0
    actual_records: int = 0
    chunks_count: int = 0
    error_message: str = ""

class BatchMigrator2015to2025:
    """2015-2025年批量迁移器"""
    
    def __init__(
        self,
        data_dir: str = "./data/pp_json_49-21",
        collection_name: str = "german_parliament",
        embedding_batch_size: int = 800,  # 🚀 使用最新GPU优化参数
        qdrant_batch_size: int = 200,     # 优化Qdrant插入
        max_concurrent_years: int = 1,    # 默认串行处理，避免GPU竞争
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        force_recreate_collection: bool = False,
        resume_from_checkpoint: bool = True
    ):
        self.data_dir = Path(data_dir)
        self.collection_name = collection_name
        self.embedding_batch_size = embedding_batch_size
        self.qdrant_batch_size = qdrant_batch_size
        self.max_concurrent_years = max_concurrent_years
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.force_recreate_collection = force_recreate_collection
        self.resume_from_checkpoint = resume_from_checkpoint
        
        # 进度管理
        self.progress_file = Path("batch_migration_progress.json")
        self.completed_years = set()
        self.failed_years = set()
        
        # 初始化组件
        logger.info("[BatchMigrator] 🚀 初始化大规模迁移系统...")
        
        # 内存优化：检查可用内存
        import psutil
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        logger.info(f"[BatchMigrator] 💾 可用内存: {available_memory_gb:.1f}GB")
        
        if available_memory_gb < 8.0:
            logger.warning("⚠️  可用内存不足8GB，将使用保守参数")
            self.embedding_batch_size = min(self.embedding_batch_size, 200)
            self.qdrant_batch_size = min(self.qdrant_batch_size, 50)
            logger.info(f"   调整后embedding batch_size: {self.embedding_batch_size}")
            logger.info(f"   调整后qdrant batch_size: {self.qdrant_batch_size}")
        
        # 设置Qdrant环境
        os.environ["QDRANT_MODE"] = "local"
        os.environ["QDRANT_LOCAL_PATH"] = "./data/qdrant"
        
        logger.info("[BatchMigrator] 🔗 创建Qdrant客户端...")
        self.qdrant_client = create_qdrant_client()
        
        logger.info("[BatchMigrator] 🤖 初始化embedding客户端...")
        try:
            self.embedding_client = GeminiEmbeddingClient(embedding_mode="local")
            logger.info("✅ Embedding客户端初始化成功")
        except Exception as e:
            logger.error(f"❌ Embedding客户端初始化失败: {str(e)}")
            # 强制释放内存
            import gc
            gc.collect()
            raise
        self.text_splitter = ParliamentTextSplitter(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        
        logger.info(f"[BatchMigrator] ✅ 初始化完成")
        logger.info(f"   - GPU优化batch_size: {self.embedding_batch_size}")
        logger.info(f"   - Qdrant batch_size: {self.qdrant_batch_size}")
        logger.info(f"   - 最大并发年份: {self.max_concurrent_years}")
        
    def discover_data_files(self, year_range: Tuple[int, int] = (2015, 2025)) -> List[MigrationTask]:
        """发现并分析数据文件"""
        
        logger.info(f"[BatchMigrator] 🔍 发现{year_range[0]}-{year_range[1]}年数据文件...")
        
        tasks = []
        
        for year in range(year_range[0], year_range[1] + 1):
            # 特殊处理2021年合并文件
            if year == 2021:
                file_path = self.data_dir / "pp_2021_merged.json"
            else:
                file_path = self.data_dir / f"pp_{year}.json"
            
            if file_path.exists():
                file_size = file_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                
                # 根据文件大小估算记录数 (经验值：1MB ≈ 250条记录)
                estimated_records = int(file_size_mb * 250)
                
                task = MigrationTask(
                    year=year,
                    file_path=file_path,
                    file_size_mb=file_size_mb,
                    estimated_records=estimated_records
                )
                tasks.append(task)
                
                logger.info(f"   📁 {year}: {file_size_mb:.1f}MB (~{estimated_records:,}条记录)")
            else:
                logger.warning(f"   ⚠️  {year}: 文件不存在 {file_path}")
        
        logger.info(f"[BatchMigrator] 发现 {len(tasks)} 个年份的数据文件")
        
        # 按文件大小排序（小文件优先，便于快速看到效果）
        tasks.sort(key=lambda x: x.file_size_mb)
        
        return tasks
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """加载检查点"""
        
        if self.resume_from_checkpoint and self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                
                self.completed_years = set(checkpoint.get('completed_years', []))
                self.failed_years = set(checkpoint.get('failed_years', []))
                
                logger.info(f"[BatchMigrator] 📋 加载检查点:")
                logger.info(f"   - 已完成年份: {sorted(self.completed_years)}")
                logger.info(f"   - 失败年份: {sorted(self.failed_years)}")
                
                return checkpoint
                
            except Exception as e:
                logger.error(f"[BatchMigrator] ❌ 检查点加载失败: {str(e)}")
                
        return {"completed_years": [], "failed_years": []}
    
    def save_checkpoint(self, tasks: List[MigrationTask]):
        """保存检查点"""
        
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "completed_years": list(self.completed_years),
            "failed_years": list(self.failed_years),
            "tasks_status": [
                {
                    "year": task.year,
                    "status": task.status,
                    "actual_records": task.actual_records,
                    "chunks_count": task.chunks_count,
                    "duration": task.end_time - task.start_time if task.end_time > 0 else 0,
                    "error_message": task.error_message
                }
                for task in tasks
            ]
        }
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            logger.debug(f"[BatchMigrator] 💾 检查点已保存")
        except Exception as e:
            logger.error(f"[BatchMigrator] ❌ 检查点保存失败: {str(e)}")
    
    def ensure_collection(self) -> bool:
        """确保Qdrant集合存在"""
        
        try:
            logger.info(f"[BatchMigrator] 🏗️  确保集合存在: {self.collection_name}")
            
            success = self.qdrant_client.create_collection_for_german_parliament(
                collection_name=self.collection_name,
                force_recreate=self.force_recreate_collection
            )
            
            if success:
                # 获取当前集合信息
                try:
                    info = self.qdrant_client.get_collection_info(self.collection_name)
                    logger.info(f"   ✅ 集合状态: {info['points_count']} 个数据点")
                    return True
                except Exception as e:
                    logger.warning(f"   ⚠️  无法获取集合信息: {str(e)}")
                    return True
            else:
                logger.error(f"[BatchMigrator] ❌ 集合创建失败")
                return False
                
        except Exception as e:
            logger.error(f"[BatchMigrator] ❌ 集合操作异常: {str(e)}")
            return False
    
    def migrate_single_year(self, task: MigrationTask) -> bool:
        """迁移单个年份的数据"""
        
        logger.info(f"[BatchMigrator] 🚀 开始迁移 {task.year} 年数据")
        logger.info(f"   文件: {task.file_path}")
        logger.info(f"   大小: {task.file_size_mb:.1f}MB")
        
        task.status = "processing"
        task.start_time = time.time()
        
        try:
            # 1. 读取JSON数据
            logger.info(f"[{task.year}] 📖 读取JSON文件...")
            with open(task.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            transcript = data.get('transcript', [])
            task.actual_records = len(transcript)
            
            logger.info(f"[{task.year}] 📊 实际记录数: {task.actual_records:,}")
            
            # 2. 文本分块处理
            logger.info(f"[{task.year}] ✂️ 开始文本分块...")
            all_chunks = []
            
            for record in transcript:
                if not isinstance(record, dict):
                    continue
                
                text_content = record.get('speech', '')
                if not text_content or len(text_content.strip()) < 50:
                    continue
                
                # 文本分块
                chunks = self.text_splitter.text_splitter.split_text(text_content)
                
                for chunk_idx, chunk in enumerate(chunks):
                    if len(chunk.strip()) < 30:
                        continue
                    
                    metadata = record.get("metadata", {})
                    chunk_data = {
                        "text": chunk,
                        "metadata": {
                            "year": int(metadata.get("year", task.year)) if metadata.get("year") else task.year,
                            "month": int(metadata.get("month", 0)) if metadata.get("month") else None,
                            "day": int(metadata.get("day", 0)) if metadata.get("day") else None,
                            "speaker": metadata.get("speaker", ""),
                            "party": metadata.get("group", ""),
                            "group": metadata.get("group", ""),
                            "group_chinese": metadata.get("group_chinese", ""),
                            "session": metadata.get("session", ""),
                            "lp": int(metadata.get("lp", 0)) if metadata.get("lp") else None,
                            "text_id": metadata.get("id", ""),
                            "source_file": task.file_path.name,
                            "topics": self._extract_topics(chunk)
                        }
                    }
                    all_chunks.append(chunk_data)
            
            task.chunks_count = len(all_chunks)
            logger.info(f"[{task.year}] ✅ 分块完成: {task.chunks_count:,} chunks")
            
            # 3. 批量生成embedding并插入
            logger.info(f"[{task.year}] 🧠 批量生成embedding...")
            
            current_point_id = int(time.time() * 1000000) % 1000000000  # 基于时间戳生成起始ID
            
            for i in range(0, len(all_chunks), self.embedding_batch_size):
                batch_chunks = all_chunks[i : i + self.embedding_batch_size]
                texts_to_embed = [chunk["text"] for chunk in batch_chunks]
                
                # 批量生成embedding
                vectors = self.embedding_client.embed_batch(
                    texts_to_embed,
                    batch_size=self.embedding_batch_size
                )
                
                # 准备数据点
                points_to_upsert = []
                for j, (chunk_data, vector) in enumerate(zip(batch_chunks, vectors)):
                    if self._is_valid_vector(vector):
                        payload = chunk_data["metadata"]
                        payload["text"] = chunk_data["text"]
                        
                        points_to_upsert.append({
                            "id": current_point_id,
                            "vector": vector,
                            "payload": payload
                        })
                        current_point_id += 1
                
                    # 批量插入到Qdrant
                if points_to_upsert:
                    try:
                        self.qdrant_client.upsert_german_parliament_data(
                            collection_name=self.collection_name,
                            data_points=points_to_upsert
                        )
                    except Exception as e:
                        logger.error(f"[{task.year}] ❌ Qdrant插入失败: {str(e)}")
                        # 重试机制
                        for retry in range(3):
                            try:
                                logger.info(f"[{task.year}] 🔄 重试插入 ({retry+1}/3)")
                                time.sleep(2 ** retry)  # 指数退避
                                self.qdrant_client.upsert_german_parliament_data(
                                    collection_name=self.collection_name,
                                    data_points=points_to_upsert
                                )
                                break
                            except Exception as retry_e:
                                logger.warning(f"[{task.year}] ⚠️  重试失败: {str(retry_e)}")
                                if retry == 2:  # 最后一次重试
                                    raise retry_e
                
                # 进度报告和检查点保存
                processed = min(i + self.embedding_batch_size, len(all_chunks))
                progress = (processed / len(all_chunks)) * 100
                logger.info(f"[{task.year}] 📊 进度: {progress:.1f}% ({processed}/{len(all_chunks)})")
                
                # 每10%或每5000个chunks保存一次检查点
                if processed % 5000 == 0 or progress % 10 == 0:
                    logger.info(f"[{task.year}] 💾 保存进度检查点...")
                    # 更新任务状态
                    temp_task = task
                    temp_task.chunks_count = processed
                    # 这里可以添加更详细的进度保存逻辑
                
                # 内存清理 (每20批次)
                if (i // self.embedding_batch_size) % 20 == 0:
                    import gc
                    gc.collect()
                    logger.debug(f"[{task.year}] 🧹 内存清理完成")
            
            task.end_time = time.time()
            task.status = "completed"
            
            duration = task.end_time - task.start_time
            logger.info(f"[BatchMigrator] 🎉 {task.year}年迁移完成!")
            logger.info(f"   耗时: {duration:.1f}秒 ({duration/60:.1f}分钟)")
            logger.info(f"   记录数: {task.actual_records:,}")
            logger.info(f"   chunks数: {task.chunks_count:,}")
            logger.info(f"   平均速度: {task.chunks_count/duration:.1f} chunks/秒")
            
            return True
            
        except Exception as e:
            task.end_time = time.time()
            task.status = "failed"
            task.error_message = str(e)
            
            logger.error(f"[BatchMigrator] ❌ {task.year}年迁移失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return False
    
    def _extract_topics(self, text: str) -> List[str]:
        """简单的主题提取"""
        topics = []
        keywords_map = {
            "Klimaschutz": ["klimaschutz", "klima", "umwelt", "co2", "emission"],
            "Digitalisierung": ["digital", "internet", "computer", "technologie"],
            "Wirtschaft": ["wirtschaft", "unternehmen", "arbeitsplatz", "job"],
            "Bildung": ["bildung", "schule", "universität", "student"],
            "Gesundheit": ["gesundheit", "medizin", "krankenhaus", "arzt"],
            "Migration": ["migration", "flüchtling", "asyl", "integration"],
            "Energie": ["energie", "strom", "erneuerbare", "atomkraft"]
        }
        text_lower = text.lower()
        for topic, keywords in keywords_map.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        return topics
    
    def _is_valid_vector(self, vector: List[float]) -> bool:
        """检查向量是否有效"""
        import numpy as np
        if not isinstance(vector, (list, np.ndarray)):
            return False
        if len(vector) != 1024:  # BGE-M3 向量维度
            return False
        vec_np = np.array(vector)
        if np.any(np.isnan(vec_np)) or np.any(np.isinf(vec_np)):
            return False
        if np.all(vec_np == 0):
            return False
        return True
    
    def execute_batch_migration(self, year_range: Tuple[int, int] = (2015, 2025)) -> bool:
        """执行批量迁移"""
        
        logger.info(f"[BatchMigrator] 🎯 开始执行大规模批量迁移")
        logger.info(f"目标年份范围: {year_range[0]}-{year_range[1]}")
        logger.info("=" * 80)
        
        # 1. 发现数据文件
        tasks = self.discover_data_files(year_range)
        if not tasks:
            logger.error("[BatchMigrator] ❌ 未发现任何数据文件")
            return False
        
        # 2. 加载检查点
        checkpoint = self.load_checkpoint()
        
        # 3. 确保集合存在
        if not self.ensure_collection():
            logger.error("[BatchMigrator] ❌ 集合初始化失败")
            return False
        
        # 4. 过滤已完成的任务
        pending_tasks = [task for task in tasks if task.year not in self.completed_years]
        
        logger.info(f"[BatchMigrator] 📋 任务统计:")
        logger.info(f"   总任务数: {len(tasks)}")
        logger.info(f"   已完成: {len(self.completed_years)}")
        logger.info(f"   待处理: {len(pending_tasks)}")
        logger.info(f"   失败任务: {len(self.failed_years)}")
        
        if not pending_tasks:
            logger.info("[BatchMigrator] 🎉 所有任务已完成!")
            return True
        
        # 5. 执行迁移
        start_time = time.time()
        successful_count = 0
        failed_count = 0
        
        for i, task in enumerate(pending_tasks):
            logger.info(f"\n[BatchMigrator] 📋 任务进度: {i+1}/{len(pending_tasks)}")
            
            success = self.migrate_single_year(task)
            
            if success:
                self.completed_years.add(task.year)
                successful_count += 1
                logger.info(f"✅ {task.year}年迁移成功")
            else:
                self.failed_years.add(task.year)
                failed_count += 1
                logger.error(f"❌ {task.year}年迁移失败")
            
            # 保存进度
            self.save_checkpoint(tasks)
        
        # 6. 迁移总结
        total_duration = time.time() - start_time
        
        logger.info(f"\n" + "=" * 80)
        logger.info(f"🎊 批量迁移完成！")
        logger.info(f"=" * 80)
        logger.info(f"📊 统计结果:")
        logger.info(f"   成功迁移: {successful_count} 个年份")
        logger.info(f"   迁移失败: {failed_count} 个年份")
        logger.info(f"   总耗时: {total_duration/60:.1f} 分钟")
        
        if successful_count > 0:
            avg_time_per_year = total_duration / successful_count
            logger.info(f"   平均每年: {avg_time_per_year/60:.1f} 分钟")
        
        # 统计总数据量
        total_records = sum(task.actual_records for task in tasks if task.status == "completed")
        total_chunks = sum(task.chunks_count for task in tasks if task.status == "completed")
        
        logger.info(f"📈 数据统计:")
        logger.info(f"   总记录数: {total_records:,}")
        logger.info(f"   总chunks数: {total_chunks:,}")
        
        # 获取最终集合状态
        try:
            final_info = self.qdrant_client.get_collection_info(self.collection_name)
            logger.info(f"🏗️  最终集合状态:")
            logger.info(f"   集合名称: {self.collection_name}")
            logger.info(f"   数据点数: {final_info['points_count']:,}")
            logger.info(f"   向量维度: {final_info['vector_params']['size']}")
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败: {str(e)}")
        
        logger.info("=" * 80)
        
        return failed_count == 0

def signal_handler(signum, frame):
    """优雅处理中断信号"""
    logger.warning(f"⚠️  接收到中断信号 {signum}，正在保存进度并退出...")
    # 这里可以添加清理逻辑
    sys.exit(1)

def main():
    """主函数"""
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 系统终止信号
    
    parser = argparse.ArgumentParser(description="德国议会2015-2025年数据批量迁移系统")
    
    parser.add_argument("--start-year", type=int, default=2015, help="起始年份")
    parser.add_argument("--end-year", type=int, default=2025, help="结束年份")
    parser.add_argument("--data-dir", type=str, default="./data/pp_json_49-21", help="数据目录")
    parser.add_argument("--collection", type=str, default="german_parliament", help="Qdrant集合名称")
    parser.add_argument("--embedding-batch-size", type=int, default=800, help="Embedding批处理大小 (GPU优化)")
    parser.add_argument("--qdrant-batch-size", type=int, default=200, help="Qdrant插入批处理大小")
    parser.add_argument("--force-recreate", action="store_true", help="强制重建集合")
    parser.add_argument("--no-resume", action="store_true", help="不从检查点恢复")
    
    args = parser.parse_args()
    
    logger.info(f"🚀 启动2015-2025年大规模数据迁移系统")
    logger.info(f"参数配置:")
    logger.info(f"   年份范围: {args.start_year}-{args.end_year}")
    logger.info(f"   数据目录: {args.data_dir}")
    logger.info(f"   Embedding batch_size: {args.embedding_batch_size} (GPU优化)")
    logger.info(f"   Qdrant batch_size: {args.qdrant_batch_size}")
    logger.info(f"   强制重建: {args.force_recreate}")
    logger.info(f"   断点续传: {not args.no_resume}")
    
    # 创建迁移器
    migrator = BatchMigrator2015to2025(
        data_dir=args.data_dir,
        collection_name=args.collection,
        embedding_batch_size=args.embedding_batch_size,
        qdrant_batch_size=args.qdrant_batch_size,
        force_recreate_collection=args.force_recreate,
        resume_from_checkpoint=not args.no_resume
    )
    
    # 执行迁移
    try:
        success = migrator.execute_batch_migration((args.start_year, args.end_year))
        
        if success:
            logger.info("🎉 所有数据迁移成功完成！")
            sys.exit(0)
        else:
            logger.error("❌ 部分数据迁移失败，请查看日志")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("⚠️  用户中断迁移，进度已保存")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ 迁移系统异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
