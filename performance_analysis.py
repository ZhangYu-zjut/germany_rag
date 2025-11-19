#!/usr/bin/env python3
"""
数据处理性能分析脚本
详细分析迁移过程中每个环节的耗时
"""

import json
import time
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import numpy as np

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.data_loader.splitter import ParliamentTextSplitter
from src.vectordb.qdrant_client import create_qdrant_client
from src.llm.embeddings import GeminiEmbeddingClient

class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, sample_size: int = 1000):
        self.sample_size = sample_size
        self.timings = {}
        
        print(f"🔍 初始化性能分析器（样本大小: {sample_size}）")
        print("=" * 60)
        
        # 初始化组件
        self.text_splitter = ParliamentTextSplitter(chunk_size=512, chunk_overlap=50)
        self.embedding_client = GeminiEmbeddingClient(embedding_mode="local")
        self.qdrant_client = create_qdrant_client(location="./performance_test_qdrant")
        
    def start_timer(self, name: str):
        """开始计时"""
        self.timings[name] = {"start": time.time()}
        
    def end_timer(self, name: str):
        """结束计时"""
        if name in self.timings:
            self.timings[name]["end"] = time.time()
            self.timings[name]["duration"] = self.timings[name]["end"] - self.timings[name]["start"]
            
    def analyze_json_parsing(self, file_path: str):
        """分析JSON解析性能"""
        print("\n📁 步骤1：JSON解析和文本预处理")
        print("-" * 40)
        
        self.start_timer("json_parsing")
        
        # JSON文件读取
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        transcript = data.get('transcript', [])
        sample_records = transcript[:self.sample_size]
        
        self.end_timer("json_parsing")
        
        print(f"✅ JSON解析完成")
        print(f"   - 文件大小: {os.path.getsize(file_path) / (1024*1024):.1f} MB")
        print(f"   - 总记录数: {len(transcript):,}")
        print(f"   - 样本记录数: {len(sample_records):,}")
        print(f"   - 解析耗时: {self.timings['json_parsing']['duration']:.3f}秒")
        
        return sample_records
        
    def analyze_text_chunking(self, records: List[Dict]):
        """分析文本分块性能"""
        print("\n✂️ 步骤2：文本分块处理")
        print("-" * 40)
        
        self.start_timer("text_chunking")
        
        all_chunks = []
        total_chars = 0
        valid_records = 0
        
        for record in records:
            if not isinstance(record, dict):
                continue
                
            text_content = record.get('speech', '')
            if not text_content or len(text_content.strip()) < 50:
                continue
                
            # 文本分块
            chunks = self.text_splitter.text_splitter.split_text(text_content)
            valid_chunks = [chunk for chunk in chunks if len(chunk.strip()) >= 30]
            
            for chunk in valid_chunks:
                chunk_data = {
                    "text": chunk,
                    "metadata": record.get("metadata", {})
                }
                all_chunks.append(chunk_data)
            
            total_chars += len(text_content)
            valid_records += 1
            
        self.end_timer("text_chunking")
        
        print(f"✅ 文本分块完成")
        print(f"   - 有效记录数: {valid_records:,}")
        print(f"   - 总字符数: {total_chars:,}")
        print(f"   - 生成chunks数: {len(all_chunks):,}")
        print(f"   - 平均每条记录chunks数: {len(all_chunks)/valid_records:.1f}")
        print(f"   - 分块耗时: {self.timings['text_chunking']['duration']:.3f}秒")
        print(f"   - 分块速度: {len(all_chunks)/self.timings['text_chunking']['duration']:.1f} chunks/秒")
        
        return all_chunks
        
    def analyze_data_validation(self, chunks: List[Dict]):
        """分析数据验证和过滤性能"""
        print("\n🔍 步骤3：数据验证和过滤")
        print("-" * 40)
        
        self.start_timer("data_validation")
        
        valid_chunks = []
        filtered_count = 0
        
        for chunk_data in chunks:
            # 验证文本内容
            text = chunk_data["text"]
            if len(text.strip()) < 30:
                filtered_count += 1
                continue
                
            # 验证元数据
            metadata = chunk_data["metadata"]
            if not metadata.get("year") or not metadata.get("speaker"):
                filtered_count += 1
                continue
                
            # 数据清洗和标准化
            cleaned_metadata = {
                "year": int(metadata.get("year", 0)) if metadata.get("year") else None,
                "month": int(metadata.get("month", 0)) if metadata.get("month") else None,
                "day": int(metadata.get("day", 0)) if metadata.get("day") else None,
                "speaker": metadata.get("speaker", "").strip(),
                "party": metadata.get("group", "").strip(),
                "session": metadata.get("session", "").strip(),
                "text": text.strip()
            }
            
            valid_chunks.append(cleaned_metadata)
            
        self.end_timer("data_validation")
        
        print(f"✅ 数据验证完成")
        print(f"   - 输入chunks数: {len(chunks):,}")
        print(f"   - 有效chunks数: {len(valid_chunks):,}")
        print(f"   - 过滤chunks数: {filtered_count:,}")
        print(f"   - 有效率: {len(valid_chunks)/len(chunks)*100:.1f}%")
        print(f"   - 验证耗时: {self.timings['data_validation']['duration']:.3f}秒")
        print(f"   - 验证速度: {len(chunks)/self.timings['data_validation']['duration']:.1f} chunks/秒")
        
        return valid_chunks
        
    def analyze_embedding_generation(self, chunks: List[Dict], batch_size: int = 150):
        """分析embedding生成性能"""
        print("\n🧠 步骤4：Embedding生成")
        print("-" * 40)
        
        self.start_timer("embedding_generation")
        
        texts_to_embed = [chunk["text"] for chunk in chunks]
        
        # 批量生成embedding
        vectors = self.embedding_client.embed_batch(
            texts_to_embed,
            batch_size=batch_size
        )
        
        self.end_timer("embedding_generation")
        
        print(f"✅ Embedding生成完成")
        print(f"   - 文本数量: {len(texts_to_embed):,}")
        print(f"   - 批次大小: {batch_size}")
        print(f"   - 生成耗时: {self.timings['embedding_generation']['duration']:.3f}秒")
        print(f"   - 生成速度: {len(texts_to_embed)/self.timings['embedding_generation']['duration']:.1f} embeddings/秒")
        
        return vectors
        
    def analyze_database_insertion(self, chunks: List[Dict], vectors: List[List[float]], batch_size: int = 100):
        """分析数据库插入性能"""
        print("\n💾 步骤5：Qdrant数据库批量插入")
        print("-" * 40)
        
        # 清理测试集合
        collection_name = "performance_test"
        try:
            self.qdrant_client.delete_collection(collection_name)
        except:
            pass
            
        # 创建测试集合
        self.qdrant_client.create_collection_for_german_parliament(
            collection_name=collection_name,
            force_recreate=True
        )
        
        self.start_timer("db_insertion")
        
        # 准备数据点
        points_to_insert = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point = {
                "id": i,
                "vector": vector,
                "payload": chunk
            }
            points_to_insert.append(point)
            
        # 批量插入
        self.qdrant_client.upsert_german_parliament_data(
            collection_name=collection_name,
            data_points=points_to_insert,
            batch_size=batch_size
        )
        
        self.end_timer("db_insertion")
        
        print(f"✅ 数据库插入完成")
        print(f"   - 数据点数: {len(points_to_insert):,}")
        print(f"   - 批次大小: {batch_size}")
        print(f"   - 插入耗时: {self.timings['db_insertion']['duration']:.3f}秒")
        print(f"   - 插入速度: {len(points_to_insert)/self.timings['db_insertion']['duration']:.1f} points/秒")
        
        # 验证插入结果
        try:
            collection_info = self.qdrant_client.get_collection_info(collection_name)
            print(f"   - 验证: 集合中有 {collection_info['points_count']} 个数据点")
        except Exception as e:
            print(f"   - 验证失败: {str(e)}")
            
    def generate_performance_report(self):
        """生成性能分析报告"""
        print("\n" + "=" * 60)
        print("📊 性能分析报告")
        print("=" * 60)
        
        total_time = sum(timing.get("duration", 0) for timing in self.timings.values())
        
        print(f"\n⏱️  各环节耗时统计:")
        print("-" * 40)
        
        step_names = {
            "json_parsing": "JSON解析和预处理",
            "text_chunking": "文本分块处理", 
            "data_validation": "数据验证和过滤",
            "embedding_generation": "Embedding生成",
            "db_insertion": "数据库批量插入"
        }
        
        for step, timing in self.timings.items():
            duration = timing.get("duration", 0)
            percentage = (duration / total_time) * 100 if total_time > 0 else 0
            
            step_name = step_names.get(step, step)
            print(f"{step_name:<20}: {duration:>8.3f}秒 ({percentage:>5.1f}%)")
            
        print("-" * 40)
        print(f"{'总计':<20}: {total_time:>8.3f}秒 (100.0%)")
        
        # 推算全量数据性能
        sample_ratio = self.sample_size / 20000  # 假设全量约2万条记录
        estimated_full_time = total_time / sample_ratio
        
        print(f"\n🔮 全量数据性能推算:")
        print(f"   - 样本比例: {sample_ratio*100:.1f}% ({self.sample_size:,}/20,000)")
        print(f"   - 推算全量处理时间: {estimated_full_time/60:.1f}分钟")
        
        # 识别主要瓶颈
        max_duration = 0
        bottleneck = ""
        for step, timing in self.timings.items():
            if timing.get("duration", 0) > max_duration:
                max_duration = timing.get("duration", 0)
                bottleneck = step_names.get(step, step)
                
        print(f"   - 🎯 主要瓶颈: {bottleneck}")
        
        return self.timings

def main():
    """主函数"""
    print("🚀 开始数据处理性能分析")
    print("=" * 60)
    
    # 使用较小样本进行快速分析
    analyzer = PerformanceAnalyzer(sample_size=500)  # 减少样本数以快速分析
    
    try:
        # 分析2019年数据
        data_file = "./data/pp_json_49-21/pp_2019.json"
        
        # 步骤1: JSON解析
        records = analyzer.analyze_json_parsing(data_file)
        
        # 步骤2: 文本分块
        chunks = analyzer.analyze_text_chunking(records)
        
        # 步骤3: 数据验证
        validated_chunks = analyzer.analyze_data_validation(chunks)
        
        # 步骤4: Embedding生成
        vectors = analyzer.analyze_embedding_generation(validated_chunks[:100])  # 只测试前100个
        
        # 步骤5: 数据库插入  
        analyzer.analyze_database_insertion(validated_chunks[:100], vectors)
        
        # 生成报告
        analyzer.generate_performance_report()
        
    except Exception as e:
        print(f"❌ 分析过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理测试数据
        try:
            analyzer.qdrant_client.delete_collection("performance_test")
            print(f"\n🧹 测试数据已清理")
        except:
            pass

if __name__ == "__main__":
    main()
