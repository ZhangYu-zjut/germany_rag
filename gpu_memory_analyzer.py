#!/usr/bin/env python3
"""
GPU显存利用率分析和优化建议
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.llm.embeddings import GeminiEmbeddingClient

def get_gpu_memory_info():
    """获取GPU显存信息"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpu_info = []
            for i, line in enumerate(lines):
                parts = [x.strip() for x in line.split(',')]
                if len(parts) >= 5:
                    gpu_info.append({
                        'gpu_id': i,
                        'total_memory': int(parts[0]),
                        'used_memory': int(parts[1]), 
                        'free_memory': int(parts[2]),
                        'utilization': int(parts[3]),
                        'temperature': int(parts[4])
                    })
            return gpu_info
    except Exception as e:
        print(f"获取GPU信息失败: {e}")
    return []

def test_batch_sizes(client: GeminiEmbeddingClient, test_texts: List[str]):
    """测试不同batch size的显存使用和性能"""
    
    print("\n🧪 测试不同batch size的性能")
    print("=" * 60)
    
    # 测试的batch size列表
    batch_sizes = [50, 100, 150, 200, 300, 400, 500, 600, 800]
    results = []
    
    for batch_size in batch_sizes:
        print(f"\n📊 测试 batch_size = {batch_size}")
        print("-" * 40)
        
        # 获取测试前GPU状态
        gpu_before = get_gpu_memory_info()
        if gpu_before:
            print(f"测试前GPU显存: {gpu_before[0]['used_memory']}/{gpu_before[0]['total_memory']} MB")
        
        try:
            # 限制测试文本数量避免过长时间
            test_batch = test_texts[:min(batch_size, len(test_texts))]
            
            start_time = time.time()
            vectors = client.embed_batch(test_batch, batch_size=batch_size)
            end_time = time.time()
            
            duration = end_time - start_time
            speed = len(test_batch) / duration
            
            # 获取测试后GPU状态
            gpu_after = get_gpu_memory_info()
            memory_used = gpu_after[0]['used_memory'] if gpu_after else 0
            memory_peak = memory_used
            
            result = {
                'batch_size': batch_size,
                'texts_processed': len(test_batch),
                'duration': duration,
                'speed': speed,
                'memory_used': memory_used,
                'memory_total': gpu_after[0]['total_memory'] if gpu_after else 16384,
                'memory_utilization': memory_used / (gpu_after[0]['total_memory'] if gpu_after else 16384) * 100,
                'gpu_utilization': gpu_after[0]['utilization'] if gpu_after else 0,
                'temperature': gpu_after[0]['temperature'] if gpu_after else 0,
                'success': True
            }
            
            results.append(result)
            
            print(f"✅ 成功")
            print(f"   处理文本数: {len(test_batch)}")
            print(f"   耗时: {duration:.2f}秒")
            print(f"   速度: {speed:.1f} embeddings/秒")
            print(f"   显存使用: {memory_used} MB ({memory_used/16384*100:.1f}%)")
            print(f"   GPU利用率: {gpu_after[0]['utilization'] if gpu_after else 0}%")
            print(f"   GPU温度: {gpu_after[0]['temperature'] if gpu_after else 0}°C")
            
            # 如果显存使用率超过90%，停止测试更大的batch size
            if memory_used > 14745:  # 90% of 16GB
                print(f"⚠️  显存使用率超过90%，停止测试更大batch size")
                break
                
        except Exception as e:
            print(f"❌ 失败: {str(e)}")
            result = {
                'batch_size': batch_size,
                'texts_processed': 0,
                'duration': 0,
                'speed': 0,
                'memory_used': 0,
                'success': False,
                'error': str(e)
            }
            results.append(result)
            
            # 如果出现OOM，停止测试
            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                print(f"🚫 检测到显存不足，停止测试")
                break
        
        # 给GPU降温时间
        time.sleep(2)
    
    return results

def analyze_results(results: List[Dict]):
    """分析测试结果并给出优化建议"""
    
    print("\n" + "=" * 60)
    print("📊 GPU性能测试结果分析")
    print("=" * 60)
    
    # 过滤成功的结果
    successful_results = [r for r in results if r['success']]
    
    if not successful_results:
        print("❌ 没有成功的测试结果")
        return
    
    # 显示结果表格
    print("\n📈 性能对比表:")
    print("-" * 80)
    print(f"{'Batch Size':<10} {'Speed(emb/s)':<12} {'Memory(MB)':<12} {'Memory%':<10} {'GPU%':<8} {'Temp°C':<8}")
    print("-" * 80)
    
    for result in successful_results:
        print(f"{result['batch_size']:<10} "
              f"{result['speed']:<12.1f} "
              f"{result['memory_used']:<12} "
              f"{result['memory_utilization']:<10.1f} "
              f"{result['gpu_utilization']:<8} "
              f"{result['temperature']:<8}")
    
    # 找到最佳配置
    best_speed = max(successful_results, key=lambda x: x['speed'])
    best_memory_efficiency = min(successful_results, key=lambda x: x['memory_utilization'])
    
    print(f"\n🎯 性能分析:")
    print(f"   最高速度: {best_speed['speed']:.1f} embeddings/秒 (batch_size={best_speed['batch_size']})")
    print(f"   当前基线: 54.7 embeddings/秒")
    print(f"   性能提升: {(best_speed['speed'] / 54.7 - 1) * 100:.1f}%")
    
    # 显存利用率分析
    max_memory_result = max(successful_results, key=lambda x: x['memory_used'])
    print(f"\n💾 显存分析:")
    print(f"   16GB显存总量: 16,384 MB")
    print(f"   最大使用: {max_memory_result['memory_used']} MB ({max_memory_result['memory_utilization']:.1f}%)")
    print(f"   剩余可用: {16384 - max_memory_result['memory_used']} MB")
    
    # 推荐配置
    print(f"\n🚀 优化建议:")
    
    # 找到在安全显存范围内的最佳batch size (85%显存以下)
    safe_results = [r for r in successful_results if r['memory_utilization'] <= 85]
    if safe_results:
        recommended = max(safe_results, key=lambda x: x['speed'])
        print(f"   推荐batch_size: {recommended['batch_size']}")
        print(f"   预期速度: {recommended['speed']:.1f} embeddings/秒")
        print(f"   显存安全度: {85 - recommended['memory_utilization']:.1f}% 余量")
    
    # 极限配置 (95%显存)
    extreme_results = [r for r in successful_results if r['memory_utilization'] <= 95]
    if extreme_results:
        extreme = max(extreme_results, key=lambda x: x['speed'])
        print(f"   极限batch_size: {extreme['batch_size']}")
        print(f"   极限速度: {extreme['speed']:.1f} embeddings/秒")
        print(f"   ⚠️  风险: 显存使用率 {extreme['memory_utilization']:.1f}%")
    
    return successful_results

def main():
    """主函数"""
    print("🔍 GPU显存利用率分析和Embedding性能优化")
    print("=" * 60)
    
    # 初始GPU状态
    gpu_info = get_gpu_memory_info()
    if gpu_info:
        print(f"\n🖥️  GPU信息:")
        for gpu in gpu_info:
            print(f"   GPU {gpu['gpu_id']}: {gpu['total_memory']} MB 总显存")
            print(f"   当前使用: {gpu['used_memory']} MB ({gpu['used_memory']/gpu['total_memory']*100:.1f}%)")
            print(f"   空闲显存: {gpu['free_memory']} MB")
            print(f"   GPU利用率: {gpu['utilization']}%")
            print(f"   GPU温度: {gpu['temperature']}°C")
    
    # 初始化embedding客户端
    print(f"\n⚡ 初始化Embedding客户端...")
    client = GeminiEmbeddingClient(embedding_mode="local")
    
    # 准备测试数据
    test_texts = [
        f"德国联邦议院第{i}次会议关于外交政策、经济政策、社会保障和环境保护等重要议题的深入讨论，涉及多个政党的不同观点和政策建议。"
        for i in range(1000)  # 生成1000条测试文本
    ]
    
    print(f"📝 准备了 {len(test_texts)} 条测试文本")
    
    try:
        # 运行batch size测试
        results = test_batch_sizes(client, test_texts)
        
        # 分析结果
        analyze_results(results)
        
    except Exception as e:
        print(f"❌ 测试过程出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
