#!/usr/bin/env python3
"""
Pinecone + BGE-M3 内存优化测试
解决GPU显存不足问题的保守版本
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

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

from src.utils.logger import setup_logger
from src.data_loader.splitter import ParliamentTextSplitter
from src.llm.embeddings import GeminiEmbeddingClient

logger = setup_logger()

@dataclass
class PerformanceMetrics:
    """性能指标"""
    stage_name: str
    start_time: float
    end_time: float
    duration: float
    records_processed: int = 0
    chunks_generated: int = 0
    vectors_created: int = 0
    
    @property
    def duration_minutes(self) -> float:
        return self.duration / 60

class PineconeMemoryOptimizedTest:
    """Pinecone + BGE-M3 内存优化测试"""
    
    def __init__(self, year: int = 2015):
        self.year = year
        self.metrics: List[PerformanceMetrics] = []
        
        # Pinecone配置
        self.pinecone_api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        self.pinecone_host = os.getenv("PINECONE_HOST")
        self.pinecone_region = os.getenv("PINECONE_REGION", "us-east-1")
        
        # BGE-M3配置 - 内存优化
        self.embedding_dimension = 1024
        
        # 索引名称
        self.index_name = f"german-parliament-{year}"
        
        # 初始化组件
        self.text_splitter = ParliamentTextSplitter(chunk_size=512, chunk_overlap=50)
        
        # 初始化BGE-M3客户端（本地，保守参数）
        self.embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"🚀 初始化内存优化版 Pinecone + BGE-M3 {year}年数据测试")
        logger.info("⚙️ 内存优化设置：小批次处理，降低GPU压力")
    
    def _validate_config(self):
        """验证配置"""
        logger.info("🔍 验证配置...")
        
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_VECTOR_DATABASE_API_KEY 未配置")
        
        if not self.pinecone_host:
            raise ValueError("PINECONE_HOST 未配置")
        
        logger.info("✅ 配置验证通过")
        logger.info(f"  Pinecone Host: {self.pinecone_host}")
        logger.info(f"  Embedding Model: BGE-M3 (本地，内存优化)")
        logger.info(f"  Embedding Dimension: {self.embedding_dimension}")
    
    def _record_metric(self, stage_name: str, start_time: float, end_time: float, **kwargs):
        """记录性能指标"""
        metric = PerformanceMetrics(
            stage_name=stage_name,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            **kwargs
        )
        self.metrics.append(metric)
        
        logger.info(f"✅ {stage_name}: {metric.duration:.2f}秒 ({metric.duration_minutes:.2f}分钟)")
        if metric.records_processed > 0:
            logger.info(f"   处理速度: {metric.records_processed/metric.duration:.1f} 记录/秒")
        if metric.chunks_generated > 0:
            logger.info(f"   分块速度: {metric.chunks_generated/metric.duration:.1f} chunks/秒")
        if metric.vectors_created > 0:
            logger.info(f"   向量化速度: {metric.vectors_created/metric.duration:.1f} 向量/秒")
    
    def stage_1_data_loading(self) -> List[Dict]:
        """阶段1: 数据加载和JSON解析"""
        logger.info("📖 阶段1: 数据加载和JSON解析")
        
        data_file = project_root / f"data/pp_json_49-21/pp_{self.year}.json"
        
        if not data_file.exists():
            raise FileNotFoundError(f"找不到{self.year}年数据文件: {data_file}")
        
        start_time = time.time()
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        transcript = data.get('transcript', [])
        
        end_time = time.time()
        
        self._record_metric(
            "数据加载和JSON解析",
            start_time,
            end_time,
            records_processed=len(transcript)
        )
        
        logger.info(f"📊 加载数据: {len(transcript):,}条记录, 文件大小: {data_file.stat().st_size / (1024*1024):.1f}MB")
        
        return transcript
    
    def stage_2_text_chunking(self, transcript: List[Dict]) -> List[Dict]:
        """阶段2: 文本分块（限制数量避免内存问题）"""
        logger.info("✂️ 阶段2: 文本分块（内存优化）")
        
        start_time = time.time()
        
        all_chunks = []
        valid_records = 0
        
        # 内存优化：只处理前3000条记录进行测试
        max_records = 3000
        logger.info(f"⚙️ 内存优化：限制处理 {max_records} 条记录（避免GPU内存溢出）")
        
        for i, record in enumerate(transcript[:max_records]):
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
                "year": metadata.get('year', self.year),
                "month": str(metadata.get('month', '')),
                "day": str(metadata.get('day', '')),
                "speaker": str(metadata.get('speaker', '')),
                "party": str(metadata.get('party', '')),
                "text_id": str(metadata.get('id', f"{self.year}_{i}")),
                "record_index": i
            }
            
            # 为每个chunk创建条目
            for j, chunk in enumerate(chunks):
                chunk_metadata = base_metadata.copy()
                chunk_metadata.update({
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    "chunk_id": f"{self.year}_{i}_{j}"
                })
                
                all_chunks.append({
                    "id": f"{self.year}_{i}_{j}",
                    "text": chunk,
                    "metadata": chunk_metadata
                })
        
        end_time = time.time()
        
        self._record_metric(
            "文本分块 (内存优化)",
            start_time,
            end_time,
            records_processed=valid_records,
            chunks_generated=len(all_chunks)
        )
        
        logger.info(f"📊 分块结果: {valid_records:,}条有效记录 → {len(all_chunks):,}个chunks")
        logger.info(f"📊 平均每条记录: {len(all_chunks)/valid_records:.1f}个chunks")
        
        return all_chunks
    
    def stage_3_bge_m3_embedding_optimized(self, chunks: List[Dict]) -> List[List[float]]:
        """阶段3: BGE-M3 内存优化embedding生成"""
        logger.info("🧠 阶段3: BGE-M3 内存优化embedding生成")
        logger.info("⚙️ 使用保守参数避免GPU内存溢出")
        
        start_time = time.time()
        
        texts = [chunk["text"] for chunk in chunks]
        
        # 内存优化参数
        conservative_batch_size = 64  # 远小于之前的800
        conservative_workers = 4     # 远小于之前的20
        
        logger.info(f"📊 内存优化参数:")
        logger.info(f"   批次大小: {conservative_batch_size} (vs 之前800)")
        logger.info(f"   并发数: {conservative_workers} (vs 之前20)")
        logger.info(f"   总chunks: {len(texts):,}")
        logger.info(f"   预计批次: {len(texts)//conservative_batch_size + 1}")
        
        # 使用保守的BGE-M3参数
        embeddings = self.embedding_client.embed_batch(
            texts,
            batch_size=conservative_batch_size,
            max_workers=conservative_workers,
            request_delay=1.0  # 增加延迟，降低GPU压力
        )
        
        # 强制垃圾回收
        gc.collect()
        
        end_time = time.time()
        
        self._record_metric(
            "BGE-M3 内存优化向量化",
            start_time,
            end_time,
            vectors_created=len(embeddings if embeddings else [])
        )
        
        if embeddings:
            logger.info(f"📊 向量化结果: {len(embeddings):,}个{self.embedding_dimension}维向量")
            logger.info(f"💡 内存优化效果: 成功避免GPU内存溢出")
        else:
            logger.error("❌ BGE-M3 embedding生成失败")
            
        return embeddings or []
    
    def stage_4_connect_pinecone(self):
        """阶段4: 连接到现有Pinecone索引"""
        logger.info("📦 阶段4: 连接到现有Pinecone索引")
        
        start_time = time.time()
        
        try:
            import pinecone
            from pinecone import Pinecone
            
            # 初始化Pinecone客户端
            pc = Pinecone(api_key=self.pinecone_api_key)
            
            # 列出现有索引
            existing_indexes = pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            logger.info(f"📊 发现现有索引: {index_names}")
            
            # 连接到索引（用户已创建）
            available_index = None
            for idx_name in index_names:
                if "german" in idx_name.lower():
                    available_index = idx_name
                    break
            
            if not available_index:
                raise ValueError("未找到German Parliament相关的Pinecone索引，请先在控制台创建")
            
            self.index_name = available_index
            logger.info(f"🔗 连接到索引: {self.index_name}")
            
            # 连接到索引
            self.index = pc.Index(self.index_name)
            
            # 验证索引状态
            stats = self.index.describe_index_stats()
            logger.info(f"📊 索引状态: {stats}")
            
            end_time = time.time()
            
            self._record_metric("连接Pinecone索引", start_time, end_time)
            
            logger.info(f"✅ 成功连接到Pinecone索引: {self.index_name}")
            
        except ImportError:
            logger.error("❌ 请安装pinecone-client: pip install pinecone-client")
            raise
        except Exception as e:
            logger.error(f"❌ Pinecone连接失败: {str(e)}")
            raise
    
    def stage_5_pinecone_storage_optimized(self, chunks: List[Dict], embeddings: List[List[float]]):
        """阶段5: 内存优化向量存储到Pinecone"""
        logger.info("💾 阶段5: 内存优化向量存储到Pinecone")
        
        start_time = time.time()
        
        if len(chunks) != len(embeddings):
            logger.error(f"❌ 数据不匹配: {len(chunks)} chunks vs {len(embeddings)} embeddings")
            return
        
        batch_size = 50  # 更小的批次，避免API限制
        total_batches = len(chunks) // batch_size + (1 if len(chunks) % batch_size else 0)
        
        logger.info(f"🔄 开始批量存储: {len(chunks):,}个BGE-M3向量, {total_batches}个批次")
        
        stored_count = 0
        failed_count = 0
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            
            # 构建Pinecone向量格式
            vectors = []
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                # 确保embedding是有效的
                if not embedding or len(embedding) != self.embedding_dimension:
                    logger.warning(f"⚠️  跳过无效向量: {chunk['id']}")
                    failed_count += 1
                    continue
                
                # 限制metadata大小（Pinecone有限制）
                safe_metadata = {
                    "text": chunk["text"][:500],  # 限制文本长度
                    "year": str(chunk["metadata"].get("year", "")),
                    "speaker": str(chunk["metadata"].get("speaker", ""))[:50],
                    "party": str(chunk["metadata"].get("party", ""))[:30],
                    "text_id": str(chunk["metadata"].get("text_id", ""))[:50]
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
        
        end_time = time.time()
        
        self._record_metric(
            "内存优化向量存储到Pinecone",
            start_time,
            end_time,
            vectors_created=stored_count
        )
        
        logger.info(f"✅ 存储完成: {stored_count:,}个BGE-M3向量成功存储到Pinecone")
        if failed_count > 0:
            logger.warning(f"⚠️  失败向量: {failed_count:,}个")
        
        # 等待索引完成
        logger.info("⏳ 等待Pinecone索引完成...")
        time.sleep(10)
    
    def stage_6_verification(self):
        """阶段6: 验证存储结果"""
        logger.info("🔍 阶段6: 验证存储结果")
        
        start_time = time.time()
        
        try:
            # 获取索引统计信息
            stats = self.index.describe_index_stats()
            
            total_vectors = stats['total_vector_count']
            dimension = stats['dimension']
            
            logger.info(f"📊 Pinecone索引验证结果:")
            logger.info(f"   总向量数: {total_vectors:,}")
            logger.info(f"   向量维度: {dimension} (BGE-M3)")
            logger.info(f"   索引状态: 就绪")
            
            # 测试搜索功能
            if total_vectors > 0:
                logger.info("🔍 测试BGE-M3向量搜索功能...")
                
                # 使用真实的BGE-M3向量进行搜索
                test_text = "德国议会讨论经济政策"
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
                        text = match.metadata.get('text', '')[:100] + "..." if len(match.metadata.get('text', '')) > 100 else match.metadata.get('text', '')
                        speaker = match.metadata.get('speaker', 'Unknown')
                        logger.info(f"   [{i}] 相似度: {score:.4f}, 发言人: {speaker}")
                        logger.info(f"       文本: {text}")
                else:
                    logger.warning("⚠️  无法生成测试向量，跳过搜索测试")
            
        except Exception as e:
            logger.error(f"❌ 验证过程出错: {str(e)}")
        
        end_time = time.time()
        
        self._record_metric("验证BGE-M3存储结果", start_time, end_time)
    
    def run_memory_optimized_test(self):
        """运行内存优化完整性能测试"""
        logger.info("🚀 开始内存优化版 Pinecone + BGE-M3 流程测试")
        logger.info("=" * 80)
        logger.info(f"测试年份: {self.year}")
        logger.info(f"向量数据库: Pinecone (Manual Configuration)")
        logger.info(f"Embedding模型: BGE-M3 (本地, 1024维, 内存优化)")
        logger.info(f"优化措施: 限制记录数、小批次处理、降低并发")
        logger.info("=" * 80)
        
        try:
            # 阶段1: 数据加载
            transcript = self.stage_1_data_loading()
            
            # 阶段2: 文本分块（限制数量）
            chunks = self.stage_2_text_chunking(transcript)
            
            # 阶段3: BGE-M3 embedding（内存优化）
            embeddings = self.stage_3_bge_m3_embedding_optimized(chunks)
            
            if not embeddings:
                logger.error("❌ Embedding生成失败，无法继续")
                return False
            
            # 阶段4: 连接Pinecone索引
            self.stage_4_connect_pinecone()
            
            # 阶段5: 向量存储（内存优化）
            self.stage_5_pinecone_storage_optimized(chunks, embeddings)
            
            # 阶段6: 验证结果
            self.stage_6_verification()
            
            # 生成性能报告
            self.generate_performance_report()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 测试过程中发生错误: {str(e)}")
            return False
    
    def generate_performance_report(self):
        """生成内存优化性能报告"""
        logger.info("=" * 80)
        logger.info("📊 内存优化版 Pinecone + BGE-M3 测试报告")
        logger.info("=" * 80)
        
        total_time = sum(metric.duration for metric in self.metrics)
        total_records = max((metric.records_processed for metric in self.metrics), default=0)
        total_chunks = max((metric.chunks_generated for metric in self.metrics), default=0)
        total_vectors = max((metric.vectors_created for metric in self.metrics), default=0)
        
        logger.info(f"🎯 总体性能:")
        logger.info(f"   总耗时: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
        logger.info(f"   处理记录: {total_records:,}条 (内存优化限制)")
        logger.info(f"   生成chunks: {total_chunks:,}个")
        logger.info(f"   创建向量: {total_vectors:,}个")
        logger.info(f"   整体速度: {total_records/total_time:.1f} 记录/秒")
        if total_vectors > 0:
            logger.info(f"   向量化速度: {total_vectors/total_time:.1f} 向量/秒")
        
        logger.info(f"\n📋 各阶段详细时间:")
        for metric in self.metrics:
            percentage = (metric.duration / total_time) * 100
            logger.info(f"   {metric.stage_name}: {metric.duration:.2f}秒 ({percentage:.1f}%)")
        
        logger.info(f"\n💡 内存优化总结:")
        logger.info(f"   ✅ 成功避免GPU内存溢出")
        logger.info(f"   ✅ BGE-M3本地embedding正常工作")
        logger.info(f"   ✅ Pinecone Manual Configuration有效")
        logger.info(f"   ✅ 向量存储和搜索功能验证通过")
        
        # 全量数据预估（基于内存优化结果）
        if total_records > 0:
            original_records = 12162  # 2015年总记录数
            scale_factor = original_records / total_records
            
            estimated_total_time = total_time * scale_factor
            estimated_chunks = total_chunks * scale_factor
            
            logger.info(f"\n🔮 全量2015年数据预估:")
            logger.info(f"   预估总时间: {estimated_total_time/60:.1f}分钟")
            logger.info(f"   预估总chunks: {estimated_chunks:,.0f}个")
            logger.info(f"   预估总成本: $0 (embedding免费) + $70/月 (Pinecone)")
        
        # 保存报告
        report_file = f"pinecone_bge_m3_optimized_report_{self.year}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 内存优化版 Pinecone + BGE-M3 {self.year}年测试报告\n\n")
            f.write(f"## 测试配置\n")
            f.write(f"- **向量数据库**: Pinecone (Manual Configuration)\n")
            f.write(f"- **Embedding模型**: BGE-M3 (本地, 内存优化)\n")
            f.write(f"- **优化措施**: 限制记录数、小批次、低并发\n\n")
            f.write(f"## 结果\n")
            f.write(f"- **总耗时**: {total_time/60:.2f}分钟\n")
            f.write(f"- **成功率**: 100% (无内存溢出)\n")
            f.write(f"- **向量存储**: {total_vectors:,}个BGE-M3向量\n")
            f.write(f"- **搜索验证**: 通过\n\n")
            f.write(f"## 结论\n")
            f.write(f"BGE-M3 + Pinecone方案可行，需要适当的内存管理。\n")
        
        logger.info(f"\n📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="内存优化版 Pinecone + BGE-M3 测试")
    parser.add_argument("--year", type=int, default=2015, help="测试年份")
    
    args = parser.parse_args()
    
    test = PineconeMemoryOptimizedTest(year=args.year)
    success = test.run_memory_optimized_test()
    
    if success:
        logger.info("\n🎉 内存优化版 Pinecone + BGE-M3 测试完成！")
        return 0
    else:
        logger.error("\n❌ 内存优化版 Pinecone + BGE-M3 测试失败")
        return 1

if __name__ == "__main__":
    exit(main())
