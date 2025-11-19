#!/usr/bin/env python3
"""
轻量级性能分析脚本
避免与后台迁移冲突，分析数据处理各环节性能
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
from src.llm.embeddings import GeminiEmbeddingClient

class LightweightPerformanceAnalyzer:
    """轻量级性能分析器（不使用Qdrant，避免冲突）"""
    
    def __init__(self, sample_size: int = 1000):
        self.sample_size = sample_size
        self.timings = {}
        
        print(f"🔍 轻量级性能分析器（样本大小: {sample_size}）")
        print("⚠️  注意：为避免与后台迁移冲突，不进行实际数据库操作")
        print("=" * 60)
        
        # 初始化组件
        self.text_splitter = ParliamentTextSplitter(chunk_size=512, chunk_overlap=50)
        
    def start_timer(self, name: str):
        """开始计时"""
        self.timings[name] = {"start": time.time()}
        
    def end_timer(self, name: str):
        """结束计时"""
        if name in self.timings:
            self.timings[name]["end"] = time.time()
            self.timings[name]["duration"] = self.timings[name]["end"] - self.timings[name]["start"]
            
    def analyze_step1_json_parsing(self, file_path: str):
        """步骤1：JSON解析和文本预处理"""
        print("\n📁 步骤1：JSON解析和文本预处理")
        print("-" * 40)
        
        self.start_timer("json_parsing")
        
        # JSON文件读取
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        transcript = data.get('transcript', [])
        sample_records = transcript[:self.sample_size]
        
        # 基础文本预处理
        processed_records = []
        total_chars = 0
        
        for record in sample_records:
            if isinstance(record, dict):
                text_content = record.get('speech', '')
                if text_content and len(text_content.strip()) >= 50:
                    processed_records.append(record)
                    total_chars += len(text_content)
        
        self.end_timer("json_parsing")
        
        print(f"✅ JSON解析和预处理完成")
        print(f"   - 文件大小: {os.path.getsize(file_path) / (1024*1024):.1f} MB")
        print(f"   - 原始记录数: {len(sample_records):,}")
        print(f"   - 有效记录数: {len(processed_records):,}")
        print(f"   - 总字符数: {total_chars:,}")
        print(f"   - 处理耗时: {self.timings['json_parsing']['duration']:.3f}秒")
        print(f"   - 处理速度: {len(processed_records)/self.timings['json_parsing']['duration']:.1f} 记录/秒")
        
        return processed_records
        
    def analyze_step2_text_chunking(self, records: List[Dict]):
        """步骤2：文本分块"""
        print("\n✂️ 步骤2：文本分块处理")
        print("-" * 40)
        
        self.start_timer("text_chunking")
        
        all_chunks = []
        total_chars = 0
        
        for record in records:
            text_content = record.get('speech', '')
            if not text_content:
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
            
        self.end_timer("text_chunking")
        
        print(f"✅ 文本分块完成")
        print(f"   - 处理记录数: {len(records):,}")
        print(f"   - 总字符数: {total_chars:,}")
        print(f"   - 生成chunks数: {len(all_chunks):,}")
        print(f"   - 平均每条记录chunks数: {len(all_chunks)/len(records):.1f}")
        print(f"   - 分块耗时: {self.timings['text_chunking']['duration']:.3f}秒")
        print(f"   - 分块速度: {len(all_chunks)/self.timings['text_chunking']['duration']:.1f} chunks/秒")
        
        return all_chunks
        
    def analyze_step3_data_validation(self, chunks: List[Dict]):
        """步骤3：数据验证和过滤"""
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
                
            # 验证和清洗元数据
            metadata = chunk_data["metadata"]
            try:
                cleaned_metadata = {
                    "year": int(metadata.get("year", 0)) if metadata.get("year") else None,
                    "month": int(metadata.get("month", 0)) if metadata.get("month") else None,
                    "day": int(metadata.get("day", 0)) if metadata.get("day") else None,
                    "speaker": metadata.get("speaker", "").strip(),
                    "party": metadata.get("group", "").strip(),
                    "session": metadata.get("session", "").strip(),
                    "text": text.strip()
                }
                
                # 基础验证
                if cleaned_metadata["year"] and cleaned_metadata["speaker"]:
                    valid_chunks.append(cleaned_metadata)
                else:
                    filtered_count += 1
                    
            except (ValueError, TypeError):
                filtered_count += 1
                continue
            
        self.end_timer("data_validation")
        
        print(f"✅ 数据验证和过滤完成")
        print(f"   - 输入chunks数: {len(chunks):,}")
        print(f"   - 有效chunks数: {len(valid_chunks):,}")
        print(f"   - 过滤chunks数: {filtered_count:,}")
        print(f"   - 有效率: {len(valid_chunks)/len(chunks)*100:.1f}%")
        print(f"   - 验证耗时: {self.timings['data_validation']['duration']:.3f}秒")
        print(f"   - 验证速度: {len(chunks)/self.timings['data_validation']['duration']:.1f} chunks/秒")
        
        return valid_chunks
        
    def analyze_step4_embedding_simulation(self, chunks: List[Dict]):
        """步骤4：Embedding生成（轻量级测试）"""
        print("\n🧠 步骤4：Embedding生成（小样本测试）")
        print("-" * 40)
        
        # 只测试前50个chunks以避免长时间运行
        test_chunks = chunks[:50]
        texts_to_embed = [chunk["text"] for chunk in test_chunks]
        
        self.start_timer("embedding_generation")
        
        # 初始化embedding客户端
        embedding_client = GeminiEmbeddingClient(embedding_mode="local")
        
        # 生成embedding
        vectors = embedding_client.embed_batch(texts_to_embed, batch_size=50)
        
        self.end_timer("embedding_generation")
        
        # 计算单个embedding的平均时间
        avg_time_per_embedding = self.timings['embedding_generation']['duration'] / len(test_chunks)
        
        print(f"✅ Embedding生成测试完成")
        print(f"   - 测试样本数: {len(test_chunks):,}")
        print(f"   - 生成耗时: {self.timings['embedding_generation']['duration']:.3f}秒")
        print(f"   - 生成速度: {len(test_chunks)/self.timings['embedding_generation']['duration']:.1f} embeddings/秒")
        print(f"   - 单个embedding平均时间: {avg_time_per_embedding:.4f}秒")
        
        return vectors, avg_time_per_embedding
        
    def analyze_step5_database_simulation(self, chunks: List[Dict], avg_embedding_time: float):
        """步骤5：数据库插入性能模拟"""
        print("\n💾 步骤5：数据库插入性能（模拟测试）")
        print("-" * 40)
        
        # 模拟数据库插入操作
        self.start_timer("db_insertion_simulation")
        
        # 模拟批量插入过程
        batch_size = 100
        total_chunks = len(chunks)
        
        # 模拟数据准备时间（创建payload等）
        preparation_time = 0
        for i in range(0, min(100, total_chunks), batch_size):
            batch_chunks = chunks[i:i+batch_size]
            
            # 模拟数据序列化和准备
            start_prep = time.time()
            for chunk in batch_chunks:
                # 模拟payload准备
                payload = {
                    "text": chunk["text"],
                    "year": chunk.get("year"),
                    "speaker": chunk.get("speaker", ""),
                    "party": chunk.get("party", "")
                }
                # 模拟向量ID生成
                point_id = hash(chunk["text"]) % 1000000
                
            preparation_time += time.time() - start_prep
            
        self.end_timer("db_insertion_simulation")
        
        # 基于已知性能数据估算实际插入时间
        # 从之前的迁移日志可知：92716个点大约需要几分钟插入时间
        estimated_insertion_rate = 500  # points/秒 (保守估计)
        estimated_insertion_time = total_chunks / estimated_insertion_rate
        
        print(f"✅ 数据库插入分析完成")
        print(f"   - 数据准备耗时: {self.timings['db_insertion_simulation']['duration']:.3f}秒")
        print(f"   - 数据准备速度: {100/self.timings['db_insertion_simulation']['duration']:.1f} points/秒")
        print(f"   - 估算插入速度: {estimated_insertion_rate} points/秒")
        print(f"   - 估算{total_chunks:,}个点插入时间: {estimated_insertion_time:.1f}秒")
        
        return estimated_insertion_time
        
    def generate_comprehensive_report(self, total_chunks: int, avg_embedding_time: float, estimated_db_time: float):
        """生成综合性能报告"""
        print("\n" + "=" * 60)
        print("📊 数据处理性能分析报告")
        print("=" * 60)
        
        # 计算各环节实际耗时
        actual_timings = {}
        
        # 步骤1-3的实际测试时间
        for step in ["json_parsing", "text_chunking", "data_validation"]:
            if step in self.timings:
                actual_timings[step] = self.timings[step]["duration"]
        
        # 步骤4: 根据小样本测试推算完整embedding时间
        full_embedding_time = total_chunks * avg_embedding_time
        actual_timings["embedding_full"] = full_embedding_time
        
        # 步骤5: 数据库插入估算时间
        actual_timings["db_insertion_full"] = estimated_db_time
        
        # 计算总时间和比例
        total_time = sum(actual_timings.values())
        
        print(f"\n⏱️  各环节耗时分析（完整数据推算）:")
        print("-" * 50)
        
        step_names = {
            "json_parsing": "1️⃣ JSON解析和预处理",
            "text_chunking": "2️⃣ 文本分块处理", 
            "data_validation": "3️⃣ 数据验证和过滤",
            "embedding_full": "4️⃣ Embedding生成",
            "db_insertion_full": "5️⃣ 数据库批量插入"
        }
        
        for step, duration in actual_timings.items():
            percentage = (duration / total_time) * 100 if total_time > 0 else 0
            step_name = step_names.get(step, step)
            
            if duration >= 60:
                time_str = f"{duration/60:>6.1f}分钟"
            else:
                time_str = f"{duration:>8.1f}秒"
                
            print(f"{step_name:<25}: {time_str} ({percentage:>5.1f}%)")
            
        print("-" * 50)
        if total_time >= 60:
            print(f"{'🕐 总计':<25}: {total_time/60:>6.1f}分钟 (100.0%)")
        else:
            print(f"{'🕐 总计':<25}: {total_time:>8.1f}秒 (100.0%)")
        
        # 识别主要瓶颈
        max_duration = 0
        bottleneck = ""
        for step, duration in actual_timings.items():
            if duration > max_duration:
                max_duration = duration
                bottleneck = step_names.get(step, step)
                
        print(f"\n🎯 性能瓶颈分析:")
        print(f"   - 主要瓶颈: {bottleneck}")
        print(f"   - 瓶颈耗时: {max_duration/60:.1f}分钟 ({max_duration/total_time*100:.1f}%)")
        
        # 对比28分钟的实际情况
        actual_28_min = 28 * 60  # 28分钟 = 1680秒
        predicted_time = total_time
        
        print(f"\n📊 预测准确性:")
        print(f"   - 实际迁移时间: {actual_28_min/60:.1f}分钟")
        print(f"   - 预测处理时间: {predicted_time/60:.1f}分钟")
        print(f"   - 预测准确度: {min(predicted_time, actual_28_min)/max(predicted_time, actual_28_min)*100:.1f}%")
        
        return actual_timings

def main():
    """主函数"""
    print("🚀 开始轻量级数据处理性能分析")
    print("=" * 60)
    
    analyzer = LightweightPerformanceAnalyzer(sample_size=1000)
    
    try:
        # 使用2019年数据进行分析
        data_file = "./data/pp_json_49-21/pp_2019.json"
        
        # 步骤1: JSON解析和预处理
        records = analyzer.analyze_step1_json_parsing(data_file)
        
        # 步骤2: 文本分块
        chunks = analyzer.analyze_step2_text_chunking(records)
        
        # 步骤3: 数据验证
        validated_chunks = analyzer.analyze_step3_data_validation(chunks)
        
        # 步骤4: Embedding生成（小样本测试）
        vectors, avg_embedding_time = analyzer.analyze_step4_embedding_simulation(validated_chunks)
        
        # 步骤5: 数据库插入（模拟）
        estimated_db_time = analyzer.analyze_step5_database_simulation(validated_chunks, avg_embedding_time)
        
        # 生成综合报告
        analyzer.generate_comprehensive_report(len(validated_chunks), avg_embedding_time, estimated_db_time)
        
    except Exception as e:
        print(f"❌ 分析过程出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
