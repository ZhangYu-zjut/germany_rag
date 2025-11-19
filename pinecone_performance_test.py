#!/usr/bin/env python3
"""
Pinecone + OpenAI text-embedding-3-large 性能测试
测试2015年数据完整流程：分块 -> OpenAI embedding -> Pinecone存储
"""

import os
import sys
import json
import time
import requests
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
    
    @property
    def records_per_second(self) -> float:
        return self.records_processed / self.duration if self.duration > 0 else 0
    
    @property
    def chunks_per_second(self) -> float:
        return self.chunks_generated / self.duration if self.duration > 0 else 0

class PineconePerformanceTest:
    """Pinecone性能测试"""
    
    def __init__(self, year: int = 2015):
        self.year = year
        self.metrics: List[PerformanceMetrics] = []
        
        # Pinecone配置
        self.pinecone_api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        self.pinecone_host = os.getenv("PINECONE_HOST")
        self.pinecone_region = os.getenv("PINECONE_REGION", "us-east-1")
        
        # OpenAI配置
        self.openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")  # 可能存储在GEMINI_API_KEY中
        self.openai_base_url = "https://api.openai.com/v1"
        self.embedding_model = "text-embedding-3-large"
        self.embedding_dimension = 1024
        
        # 索引名称
        self.index_name = f"german-parliament-{year}"
        
        # 初始化组件
        self.text_splitter = ParliamentTextSplitter(chunk_size=512, chunk_overlap=50)
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"🚀 初始化Pinecone {year}年数据性能测试")
    
    def _validate_config(self):
        """验证配置"""
        logger.info("🔍 验证配置...")
        
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_VECTOR_DATABASE_API_KEY 未配置")
        
        if not self.pinecone_host:
            raise ValueError("PINECONE_HOST 未配置")
            
        if not self.openai_api_key:
            raise ValueError("OpenAI API Key 未配置（OPENAI_API_KEY 或 GEMINI_API_KEY）")
        
        logger.info("✅ 配置验证通过")
        logger.info(f"  Pinecone Host: {self.pinecone_host}")
        logger.info(f"  Pinecone Region: {self.pinecone_region}")
        logger.info(f"  OpenAI Model: {self.embedding_model}")
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
            logger.info(f"   处理速度: {metric.records_per_second:.1f} 记录/秒")
        if metric.chunks_generated > 0:
            logger.info(f"   分块速度: {metric.chunks_per_second:.1f} chunks/秒")
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
    
    def stage_3_openai_embedding(self, chunks: List[Dict]) -> List[List[float]]:
        """阶段3: OpenAI embedding生成"""
        logger.info(f"🧠 阶段3: OpenAI {self.embedding_model} embedding生成")
        
        start_time = time.time()
        
        texts = [chunk["text"] for chunk in chunks]
        
        # 使用OpenAI API进行embedding
        embeddings = self._generate_openai_embeddings_batch(
            texts,
            batch_size=1000,  # OpenAI支持更大的批次
            max_workers=10,
            request_delay=1.0  # OpenAI需要更保守的延迟
        )
        
        end_time = time.time()
        
        self._record_metric(
            f"OpenAI {self.embedding_model} 向量化",
            start_time,
            end_time,
            vectors_created=len(embeddings)
        )
        
        logger.info(f"📊 向量化结果: {len(embeddings):,}个{self.embedding_dimension}维向量")
        
        return embeddings
    
    def _generate_openai_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 1000,
        max_workers: int = 10,
        request_delay: float = 1.0
    ) -> List[List[float]]:
        """批量生成OpenAI embeddings"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        def embed_single_batch(batch_texts: List[str]) -> List[List[float]]:
            try:
                url = f"{self.openai_base_url}/embeddings"
                
                payload = {
                    "model": self.embedding_model,
                    "input": batch_texts,
                    "dimensions": self.embedding_dimension
                }
                
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    return [item["embedding"] for item in data["data"]]
                else:
                    logger.error(f"❌ OpenAI API错误: {response.status_code} - {response.text}")
                    return []
                    
            except Exception as e:
                logger.error(f"❌ OpenAI embedding批次异常: {str(e)}")
                return []
        
        all_embeddings = []
        total_batches = len(texts) // batch_size + (1 if len(texts) % batch_size else 0)
        
        logger.info(f"🔄 开始OpenAI批量embedding: {len(texts):,}个文本, {total_batches}个批次")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有批次任务
            future_to_batch = {}
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                future = executor.submit(embed_single_batch, batch)
                future_to_batch[future] = i // batch_size + 1
                
                # 延迟提交以避免API限制
                if request_delay > 0:
                    time.sleep(request_delay)
            
            # 收集结果
            completed_batches = 0
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    batch_embeddings = future.result()
                    if batch_embeddings:
                        all_embeddings.extend(batch_embeddings)
                        completed_batches += 1
                        
                        if completed_batches % 5 == 0:  # 每5个批次报告进度
                            progress = (completed_batches / total_batches) * 100
                            logger.info(f"📈 OpenAI Embedding进度: {progress:.1f}% ({completed_batches}/{total_batches})")
                    else:
                        logger.warning(f"⚠️  批次{batch_num}返回空结果")
                        
                except Exception as e:
                    logger.error(f"❌ 批次{batch_num}处理失败: {str(e)}")
        
        logger.info(f"✅ OpenAI Embedding完成: {len(all_embeddings):,}/{len(texts):,}个向量")
        return all_embeddings
    
    def stage_4_create_pinecone_index(self):
        """阶段4: 创建Pinecone索引"""
        logger.info("📦 阶段4: 创建Pinecone索引")
        
        start_time = time.time()
        
        # Pinecone客户端初始化
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
            
            # 创建新索引
            logger.info(f"🔨 创建新索引: {self.index_name}")
            pc.create_index(
                name=self.index_name,
                dimension=self.embedding_dimension,
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
            
            self._record_metric("创建Pinecone索引", start_time, end_time)
            
            logger.info(f"✅ Pinecone索引创建成功: {self.index_name}")
            
        except ImportError:
            logger.error("❌ 请安装pinecone-client: pip install pinecone-client")
            raise
        except Exception as e:
            logger.error(f"❌ Pinecone索引创建失败: {str(e)}")
            raise
    
    def stage_5_pinecone_storage(self, chunks: List[Dict], embeddings: List[List[float]]):
        """阶段5: 向量存储到Pinecone"""
        logger.info("💾 阶段5: 向量存储到Pinecone")
        
        start_time = time.time()
        
        batch_size = 100  # Pinecone推荐批次大小
        total_batches = len(chunks) // batch_size + (1 if len(chunks) % batch_size else 0)
        
        logger.info(f"🔄 开始批量存储: {len(chunks):,}个向量, {total_batches}个批次")
        
        stored_count = 0
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            
            # 构建Pinecone向量格式
            vectors = []
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                vectors.append({
                    "id": chunk["id"],
                    "values": embedding,
                    "metadata": {
                        "text": chunk["text"][:1000],  # Pinecone metadata有大小限制
                        **{k: str(v)[:100] for k, v in chunk["metadata"].items()}  # 确保metadata字符串不太长
                    }
                })
            
            # 插入到Pinecone
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
            "向量存储到Pinecone",
            start_time,
            end_time,
            vectors_created=stored_count
        )
        
        logger.info(f"✅ 存储完成: {stored_count:,}个向量成功存储到Pinecone")
        
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
            logger.info(f"   向量维度: {dimension}")
            logger.info(f"   索引状态: 就绪")
            
            # 测试搜索功能
            if total_vectors > 0:
                logger.info("🔍 测试搜索功能...")
                # 创建一个测试向量（全1向量）
                test_vector = [0.001] * self.embedding_dimension
                
                search_results = self.index.query(
                    vector=test_vector,
                    top_k=3,
                    include_metadata=True
                )
                
                logger.info(f"✅ 搜索测试成功，返回 {len(search_results.matches)} 个结果")
            
        except Exception as e:
            logger.error(f"❌ 验证过程出错: {str(e)}")
        
        end_time = time.time()
        
        self._record_metric("验证存储结果", start_time, end_time)
    
    def run_complete_test(self):
        """运行完整性能测试"""
        logger.info("🚀 开始Pinecone + OpenAI完整流程性能测试")
        logger.info("=" * 80)
        logger.info(f"测试年份: {self.year}")
        logger.info(f"向量数据库: Pinecone")
        logger.info(f"Embedding模型: OpenAI {self.embedding_model}")
        logger.info("=" * 80)
        
        try:
            # 阶段1: 数据加载
            transcript = self.stage_1_data_loading()
            
            # 阶段2: 文本分块
            chunks = self.stage_2_text_chunking(transcript)
            
            # 阶段3: OpenAI embedding
            embeddings = self.stage_3_openai_embedding(chunks)
            
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
        logger.info("📊 Pinecone + OpenAI 性能测试报告")
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
        
        # 计算成本估算
        # OpenAI text-embedding-3-large 定价: $0.13/1M tokens
        # 假设每个chunk平均100 tokens
        estimated_tokens = total_chunks * 100
        embedding_cost = (estimated_tokens / 1_000_000) * 0.13
        
        logger.info(f"\n💰 成本估算 ({self.year}年):")
        logger.info(f"   预估tokens: {estimated_tokens:,}")
        logger.info(f"   OpenAI embedding成本: ${embedding_cost:.3f}")
        
        # 全量数据预估
        if total_records > 0:
            total_data_records = 835689  # 所有年份总记录数
            scale_factor = total_data_records / total_records
            
            estimated_total_time = total_time * scale_factor
            estimated_total_cost = embedding_cost * scale_factor
            
            logger.info(f"\n🔮 全量数据预估:")
            logger.info(f"   预估总时间: {estimated_total_time/60:.1f}分钟 ({estimated_total_time/3600:.2f}小时)")
            logger.info(f"   预估总成本: ${estimated_total_cost:.2f}")
        
        # 保存报告到文件
        report_file = f"pinecone_performance_report_{self.year}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Pinecone + OpenAI {self.year}年数据性能测试报告\n\n")
            f.write(f"## 配置信息\n")
            f.write(f"- **向量数据库**: Pinecone\n")
            f.write(f"- **Embedding模型**: OpenAI {self.embedding_model}\n")
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
                f.write(f"- **耗时**: {metric.duration:.2f}秒 ({percentage:.1f}%)\n")
                if metric.records_processed > 0:
                    f.write(f"- **处理速度**: {metric.records_per_second:.1f} 记录/秒\n")
                if metric.chunks_generated > 0:
                    f.write(f"- **分块速度**: {metric.chunks_per_second:.1f} chunks/秒\n")
                if metric.vectors_created > 0:
                    f.write(f"- **向量化速度**: {metric.vectors_created/metric.duration:.1f} 向量/秒\n")
                f.write("\n")
            
            f.write(f"## 成本分析\n")
            f.write(f"- **预估tokens**: {estimated_tokens:,}\n")
            f.write(f"- **单年embedding成本**: ${embedding_cost:.3f}\n")
            if total_records > 0:
                f.write(f"- **全量数据预估成本**: ${estimated_total_cost:.2f}\n")
            f.write("\n")
        
        logger.info(f"\n📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pinecone + OpenAI性能测试")
    parser.add_argument("--year", type=int, default=2015, help="测试年份")
    
    args = parser.parse_args()
    
    test = PineconePerformanceTest(year=args.year)
    success = test.run_complete_test()
    
    if success:
        logger.info("\n🎉 Pinecone性能测试完成！")
        return 0
    else:
        logger.error("\n❌ Pinecone性能测试失败")
        return 1

if __name__ == "__main__":
    exit(main())

