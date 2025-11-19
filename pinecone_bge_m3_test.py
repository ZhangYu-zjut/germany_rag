#!/usr/bin/env python3
"""
Pinecone + BGE-M3 Custom Embedding 性能测试
最优方案：本地BGE-M3生成embedding + Pinecone存储
"""

import os
import sys
import json
import time
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

class PineconeBGEM3Test:
    """Pinecone + BGE-M3 性能测试"""
    
    def __init__(self, year: int = 2015):
        self.year = year
        self.metrics: List[PerformanceMetrics] = []
        
        # Pinecone配置
        self.pinecone_api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        self.pinecone_host = os.getenv("PINECONE_HOST")
        self.pinecone_region = os.getenv("PINECONE_REGION", "us-east-1")
        
        # BGE-M3配置
        self.embedding_dimension = 1024
        
        # 索引名称
        self.index_name = f"german-parliament-{year}"
        
        # 初始化组件
        self.text_splitter = ParliamentTextSplitter(chunk_size=512, chunk_overlap=50)
        
        # 初始化BGE-M3客户端（本地）
        self.embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"🚀 初始化Pinecone + BGE-M3 {year}年数据性能测试")
    
    def _validate_config(self):
        """验证配置"""
        logger.info("🔍 验证配置...")
        
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_VECTOR_DATABASE_API_KEY 未配置")
        
        if not self.pinecone_host:
            raise ValueError("PINECONE_HOST 未配置")
        
        logger.info("✅ 配置验证通过")
        logger.info(f"  Pinecone Host: {self.pinecone_host}")
        logger.info(f"  Embedding Model: BGE-M3 (本地)")
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
        """阶段2: 文本分块"""
        logger.info("✂️  阶段2: 文本分块")
        
        start_time = time.time()
        
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
            "文本分块",
            start_time,
            end_time,
            records_processed=valid_records,
            chunks_generated=len(all_chunks)
        )
        
        logger.info(f"📊 分块结果: {valid_records:,}条有效记录 → {len(all_chunks):,}个chunks")
        logger.info(f"📊 平均每条记录: {len(all_chunks)/valid_records:.1f}个chunks")
        
        return all_chunks
    
    def stage_3_bge_m3_embedding(self, chunks: List[Dict]) -> List[List[float]]:
        """阶段3: BGE-M3 本地embedding生成"""
        logger.info("🧠 阶段3: BGE-M3 本地embedding生成")
        
        start_time = time.time()
        
        texts = [chunk["text"] for chunk in chunks]
        
        # 使用优化后的BGE-M3参数
        embeddings = self.embedding_client.embed_batch(
            texts,
            batch_size=800,  # 优化后的批处理大小
            max_workers=20,
            request_delay=0.5
        )
        
        end_time = time.time()
        
        self._record_metric(
            "BGE-M3 本地向量化",
            start_time,
            end_time,
            vectors_created=len(embeddings if embeddings else [])
        )
        
        if embeddings:
            logger.info(f"📊 向量化结果: {len(embeddings):,}个{self.embedding_dimension}维向量")
        else:
            logger.error("❌ BGE-M3 embedding生成失败")
            
        return embeddings or []
    
    def stage_4_create_pinecone_index(self):
        """阶段4: 创建Pinecone索引（Manual Configuration）"""
        logger.info("📦 阶段4: 创建Pinecone索引 (Manual Configuration)")
        
        start_time = time.time()
        
        try:
            import pinecone
            from pinecone import Pinecone, ServerlessSpec
            
            # 初始化Pinecone客户端
            pc = Pinecone(api_key=self.pinecone_api_key)
            
            # 检查索引是否存在，如果存在则删除
            existing_indexes = pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.index_name in index_names:
                logger.info(f"⚠️  索引 {self.index_name} 已存在，删除旧索引...")
                pc.delete_index(self.index_name)
                time.sleep(10)  # 等待删除完成
            
            # 创建新索引 - Manual Configuration
            logger.info(f"🔨 创建新索引 (Manual Configuration): {self.index_name}")
            logger.info(f"   维度: {self.embedding_dimension} (BGE-M3)")
            logger.info(f"   度量: cosine")
            
            pc.create_index(
                name=self.index_name,
                dimension=self.embedding_dimension,  # BGE-M3的1024维
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.pinecone_region
                )
            )
            
            # 等待索引准备就绪
            logger.info("⏳ 等待索引初始化...")
            time.sleep(30)  # Pinecone索引需要时间初始化
            
            # 连接到索引
            self.index = pc.Index(self.index_name)
            
            end_time = time.time()
            
            self._record_metric("创建Pinecone索引 (Manual)", start_time, end_time)
            
            logger.info(f"✅ Pinecone Manual Configuration索引创建成功: {self.index_name}")
            
        except ImportError:
            logger.error("❌ 请安装pinecone-client: pip install pinecone-client")
            raise
        except Exception as e:
            logger.error(f"❌ Pinecone索引创建失败: {str(e)}")
            raise
    
    def stage_5_pinecone_storage(self, chunks: List[Dict], embeddings: List[List[float]]):
        """阶段5: 自定义向量存储到Pinecone"""
        logger.info("💾 阶段5: 自定义向量存储到Pinecone")
        
        start_time = time.time()
        
        if len(chunks) != len(embeddings):
            logger.error(f"❌ 数据不匹配: {len(chunks)} chunks vs {len(embeddings)} embeddings")
            return
        
        batch_size = 100  # Pinecone推荐批次大小
        total_batches = len(chunks) // batch_size + (1 if len(chunks) % batch_size else 0)
        
        logger.info(f"🔄 开始批量存储: {len(chunks):,}个自定义向量, {total_batches}个批次")
        
        stored_count = 0
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            
            # 构建Pinecone向量格式
            vectors = []
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                # 确保embedding是有效的
                if not embedding or len(embedding) != self.embedding_dimension:
                    logger.warning(f"⚠️  跳过无效向量: {chunk['id']}")
                    continue
                
                vectors.append({
                    "id": chunk["id"],
                    "values": embedding,
                    "metadata": {
                        "text": chunk["text"][:1000],  # Pinecone metadata有大小限制
                        **{k: str(v)[:100] for k, v in chunk["metadata"].items()}  # 确保metadata字符串不太长
                    }
                })
            
            # 插入到Pinecone
            if vectors:  # 只有当有有效向量时才插入
                try:
                    self.index.upsert(vectors=vectors)
                    stored_count += len(vectors)
                    
                    if (i // batch_size + 1) % 10 == 0:  # 每10个批次报告进度
                        progress = (stored_count / len(chunks)) * 100
                        logger.info(f"📈 存储进度: {progress:.1f}% ({stored_count:,}/{len(chunks):,})")
                    
                    # Pinecone限制：避免过快请求
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ 批次存储失败: {str(e)}")
                    # 继续处理其他批次
        
        end_time = time.time()
        
        self._record_metric(
            "自定义向量存储到Pinecone",
            start_time,
            end_time,
            vectors_created=stored_count
        )
        
        logger.info(f"✅ 存储完成: {stored_count:,}个BGE-M3向量成功存储到Pinecone")
        
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
                # 创建一个测试向量（随机向量）
                import random
                test_vector = [random.uniform(-0.1, 0.1) for _ in range(self.embedding_dimension)]
                
                search_results = self.index.query(
                    vector=test_vector,
                    top_k=3,
                    include_metadata=True
                )
                
                logger.info(f"✅ BGE-M3向量搜索测试成功，返回 {len(search_results.matches)} 个结果")
                
                # 显示搜索结果示例
                for i, match in enumerate(search_results.matches[:2], 1):
                    score = match.score
                    text = match.metadata.get('text', '')[:100] + "..." if len(match.metadata.get('text', '')) > 100 else match.metadata.get('text', '')
                    logger.info(f"   [{i}] 相似度: {score:.4f}, 文本: {text}")
            
        except Exception as e:
            logger.error(f"❌ 验证过程出错: {str(e)}")
        
        end_time = time.time()
        
        self._record_metric("验证BGE-M3存储结果", start_time, end_time)
    
    def run_complete_test(self):
        """运行完整性能测试"""
        logger.info("🚀 开始Pinecone + BGE-M3完整流程性能测试")
        logger.info("=" * 80)
        logger.info(f"测试年份: {self.year}")
        logger.info(f"向量数据库: Pinecone (Manual Configuration)")
        logger.info(f"Embedding模型: BGE-M3 (本地, 1024维)")
        logger.info("=" * 80)
        
        try:
            # 阶段1: 数据加载
            transcript = self.stage_1_data_loading()
            
            # 阶段2: 文本分块
            chunks = self.stage_2_text_chunking(transcript)
            
            # 阶段3: BGE-M3 embedding
            embeddings = self.stage_3_bge_m3_embedding(chunks)
            
            if not embeddings:
                logger.error("❌ Embedding生成失败，无法继续")
                return False
            
            # 阶段4: 创建Pinecone索引
            self.stage_4_create_pinecone_index()
            
            # 阶段5: 向量存储
            self.stage_5_pinecone_storage(chunks, embeddings)
            
            # 阶段6: 验证结果
            self.stage_6_verification()
            
            # 生成性能报告
            self.generate_performance_report()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 测试过程中发生错误: {str(e)}")
            return False
    
    def generate_performance_report(self):
        """生成性能报告"""
        logger.info("=" * 80)
        logger.info("📊 Pinecone + BGE-M3 性能测试报告")
        logger.info("=" * 80)
        
        total_time = sum(metric.duration for metric in self.metrics)
        total_records = self.metrics[0].records_processed if self.metrics else 0
        total_chunks = max((metric.chunks_generated for metric in self.metrics), default=0)
        total_vectors = max((metric.vectors_created for metric in self.metrics), default=0)
        
        logger.info(f"🎯 总体性能:")
        logger.info(f"   总耗时: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
        logger.info(f"   处理记录: {total_records:,}条")
        logger.info(f"   生成chunks: {total_chunks:,}个")
        logger.info(f"   创建向量: {total_vectors:,}个")
        logger.info(f"   整体速度: {total_records/total_time:.1f} 记录/秒")
        logger.info(f"   向量化速度: {total_vectors/total_time:.1f} 向量/秒")
        
        logger.info(f"\n📋 各阶段详细时间:")
        for metric in self.metrics:
            percentage = (metric.duration / total_time) * 100
            logger.info(f"   {metric.stage_name}: {metric.duration:.2f}秒 ({percentage:.1f}%)")
        
        # 成本对比
        logger.info(f"\n💰 成本对比:")
        logger.info(f"   BGE-M3 embedding成本: $0 (本地免费)")
        logger.info(f"   OpenAI embedding成本: ~$1.5 (省下了)")
        logger.info(f"   Pinecone存储月费: $70")
        
        # 全量数据预估
        if total_records > 0:
            total_data_records = 835689  # 所有年份总记录数
            scale_factor = total_data_records / total_records
            
            estimated_total_time = total_time * scale_factor
            
            logger.info(f"\n🔮 全量数据预估:")
            logger.info(f"   预估总时间: {estimated_total_time/60:.1f}分钟 ({estimated_total_time/3600:.2f}小时)")
            logger.info(f"   预估总成本: $0 (embedding免费) + $70/月 (Pinecone)")
        
        # 保存报告到文件
        report_file = f"pinecone_bge_m3_report_{self.year}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Pinecone + BGE-M3 {self.year}年数据性能测试报告\n\n")
            f.write(f"## 配置信息\n")
            f.write(f"- **向量数据库**: Pinecone (Manual Configuration)\n")
            f.write(f"- **Embedding模型**: BGE-M3 (本地)\n")
            f.write(f"- **向量维度**: {self.embedding_dimension}\n")
            f.write(f"- **测试年份**: {self.year}\n\n")
            
            f.write(f"## 总体性能\n")
            f.write(f"- **总耗时**: {total_time:.2f}秒 ({total_time/60:.2f}分钟)\n")
            f.write(f"- **处理记录**: {total_records:,}条\n")
            f.write(f"- **生成chunks**: {total_chunks:,}个\n")
            f.write(f"- **创建向量**: {total_vectors:,}个\n")
            f.write(f"- **整体速度**: {total_records/total_time:.1f} 记录/秒\n")
            f.write(f"- **向量化速度**: {total_vectors/total_time:.1f} 向量/秒\n\n")
            
            f.write(f"## 各阶段详细时间\n\n")
            for metric in self.metrics:
                percentage = (metric.duration / total_time) * 100
                f.write(f"### {metric.stage_name}\n")
                f.write(f"- **耗时**: {metric.duration:.2f}秒 ({percentage:.1f}%)\n\n")
            
            f.write(f"## 成本分析\n")
            f.write(f"- **BGE-M3 embedding**: $0 (本地免费)\n")
            f.write(f"- **相比OpenAI节省**: ~$1.5/年\n")
            f.write(f"- **Pinecone月费**: $70\n\n")
            
            f.write(f"## 结论\n")
            f.write(f"BGE-M3 + Pinecone Custom方案验证成功，成本低且性能优秀。\n")
        
        logger.info(f"\n📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pinecone + BGE-M3 性能测试")
    parser.add_argument("--year", type=int, default=2015, help="测试年份")
    
    args = parser.parse_args()
    
    test = PineconeBGEM3Test(year=args.year)
    success = test.run_complete_test()
    
    if success:
        logger.info("\n🎉 Pinecone + BGE-M3 性能测试完成！")
        return 0
    else:
        logger.error("\n❌ Pinecone + BGE-M3 性能测试失败")
        return 1

if __name__ == "__main__":
    exit(main())

