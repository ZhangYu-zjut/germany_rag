"""
端到端真实环境测试
使用2018-2020年的真实数据，验证完整流程：
1. 数据加载和索引构建
2. 完整工作流运行
3. 输出质量验证

新增功能：
- 中间断点检测和缓存机制
- 智能跳过已完成的步骤
- 支持从任意步骤开始运行
"""

import sys
import os
import pickle
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import logger
from src.data_loader import ParliamentDataLoader, ParliamentTextSplitter, MetadataMapper
from src.llm import GeminiEmbeddingClient
from src.vectordb import MilvusClient, MilvusCollectionManager
from src.graph.workflow import QuestionAnswerWorkflow
from src.graph.state import create_initial_state


# ========== 缓存管理 ==========

def get_cache_dir():
    """获取缓存目录"""
    cache_dir = Path("cache/e2e_test")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_data_hash(years: list, chunk_size: int, chunk_overlap: int):
    """生成数据配置的哈希值，用于缓存键"""
    config_str = f"years:{','.join(sorted(years))}_chunk:{chunk_size}_overlap:{chunk_overlap}"
    return hashlib.md5(config_str.encode()).hexdigest()[:12]


def save_to_cache(data, cache_key: str, step_name: str):
    """保存数据到缓存"""
    cache_dir = get_cache_dir()
    cache_file = cache_dir / f"{step_name}_{cache_key}.pkl"
    
    print(f"💾 保存缓存: {cache_file}")
    with open(cache_file, 'wb') as f:
        pickle.dump({
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'cache_key': cache_key
        }, f)
    return cache_file


def load_from_cache(cache_key: str, step_name: str):
    """从缓存加载数据"""
    cache_dir = get_cache_dir()
    cache_file = cache_dir / f"{step_name}_{cache_key}.pkl"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'rb') as f:
            cached = pickle.load(f)
        
        print(f"📂 加载缓存: {cache_file}")
        print(f"   缓存时间: {cached['timestamp']}")
        return cached['data']
    except Exception as e:
        print(f"⚠️ 缓存文件损坏，将重新生成: {e}")
        return None


def check_milvus_collection_status():
    """检查Milvus collection状态"""
    try:
        collection_name = os.getenv("MILVUS_COLLECTION_NAME", "parliament_speeches")
        
        with MilvusClient() as client:
            from pymilvus import utility
            
            if not utility.has_collection(collection_name):
                return {"exists": False, "count": 0}
            
            # 获取collection
            from pymilvus import Collection
            collection = Collection(collection_name)
            count = collection.num_entities
            
            return {
                "exists": True, 
                "count": count,
                "collection_name": collection_name
            }
    except Exception as e:
        print(f"⚠️ 检查Milvus状态失败: {e}")
        return {"exists": False, "count": 0, "error": str(e)}


def build_index_for_years(years: list, force_rebuild: bool = False):
    """
    为指定年份构建Milvus索引（支持断点续传）
    
    Args:
        years: 年份列表，如 ['2018', '2019', '2020']
        force_rebuild: 是否强制重建（忽略缓存）
    
    Returns:
        (speeches_count, chunks_count, vectors_count)
    """
    print("\n" + "="*80)
    print("📚 步骤1: 构建索引 - 智能断点检测模式")
    print("="*80)
    
    # 获取配置参数
    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    cache_key = get_data_hash(years, chunk_size, chunk_overlap)
    
    print(f"📋 配置信息:")
    print(f"   - 处理年份: {years}")
    print(f"   - 文本块大小: {chunk_size}")
    print(f"   - 重叠长度: {chunk_overlap}")
    print(f"   - 缓存键: {cache_key}")
    print(f"   - 强制重建: {'是' if force_rebuild else '否'}")
    
    # ========== 检查Milvus状态 ==========
    print(f"\n🔍 检查现有索引状态...")
    milvus_status = check_milvus_collection_status()
    
    if milvus_status["exists"] and milvus_status["count"] > 0 and not force_rebuild:
        print(f"✅ 发现现有索引:")
        print(f"   - Collection: {milvus_status.get('collection_name')}")
        print(f"   - 向量数量: {milvus_status['count']}")
        
        try:
            use_existing = input("\n🤔 是否使用现有索引？(y/n，默认y): ").strip().lower()
        except EOFError:
            # 非交互模式下默认使用现有索引
            use_existing = 'y'
            print("y (非交互模式，自动选择)")
        
        if not use_existing or use_existing == 'y':
            print("✅ 使用现有索引，跳过构建步骤")
            # 需要获取原始数据统计信息来返回正确的计数
            try:
                # 快速加载数据以获取统计信息
                data_dir = Path("data/pp_json_49-21")
                loader = ParliamentDataLoader(
                    data_dir=str(data_dir),
                    data_mode="PART",
                    years=years
                )
                speeches = loader.load_data()
                splitter = ParliamentTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                chunks = splitter.split_speeches(speeches)
                
                return len(speeches), len(chunks), milvus_status["count"]
            except Exception as e:
                print(f"⚠️ 无法获取数据统计: {e}")
                return 0, 0, milvus_status["count"]
    
    # ========== 步骤1.1-1.3: 数据准备 ==========
    enriched_chunks = None
    
    # 检查是否有数据准备缓存
    if not force_rebuild:
        enriched_chunks = load_from_cache(cache_key, "data_prepared")
    
    if enriched_chunks is None:
        print("\n[1.1] 加载数据...")
        data_dir = Path("data/pp_json_49-21")
        
        loader = ParliamentDataLoader(
            data_dir=str(data_dir),
            data_mode="PART",
            years=years
        )
        
        speeches = loader.load_data()
        stats = loader.get_statistics(speeches)
        
        print(f"✅ 数据加载完成:")
        print(f"   - 演讲记录: {len(speeches)} 条")
        print(f"   - 年份分布: {list(stats['years'].keys())}")
        print(f"   - 发言人数: {stats['speakers_count']}")
        
        if len(speeches) == 0:
            raise ValueError("未加载到任何数据，请检查数据文件是否存在")
        
        print("\n[1.2] 文本分块...")
        splitter = ParliamentTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_speeches(speeches)
        print(f"✅ 分块完成: {len(chunks)} 个文本块")
        
        print("\n[1.3] 元数据丰富...")
        mapper = MetadataMapper()
        enriched_chunks = mapper.enrich_chunks(chunks)
        print(f"✅ 元数据丰富完成")
        
        # 保存数据准备结果到缓存
        save_to_cache(enriched_chunks, cache_key, "data_prepared")
        save_to_cache({
            'speeches_count': len(speeches),
            'chunks_count': len(chunks)
        }, cache_key, "data_stats")
    else:
        print("📂 从缓存加载数据准备结果...")
        print(f"✅ 数据准备完成: {len(enriched_chunks)} 个enriched chunks")
    
    # ========== 步骤1.4: 生成Embedding ==========
    embedded_chunks = None
    
    # 检查是否有Embedding缓存
    if not force_rebuild:
        embedded_chunks = load_from_cache(cache_key, "embeddings")
    
    if embedded_chunks is None:
        print("\n[1.4] 生成Embedding...")
        embedding_client = GeminiEmbeddingClient()
        
        # 根据模式调整参数
        embedding_mode = os.getenv("EMBEDDING_MODE", "deepinfra")
        if embedding_mode == "local":
            print("⏳ 开始批量Embedding（本地BGE-M3模式：GPU加速）...")
            print(f"   总数据量: {len(enriched_chunks)} 条")
            print(f"   批处理大小: 64条/批（GPU优化）")
            print(f"   执行方式: 本地GPU加速（无需并发和延迟）")
            batch_size = 64  # GPU 可以使用更大的批次
            max_workers = 1  # 本地模型不需要并发
            request_delay = 0.0  # 本地模型不需要延迟
        else:
            print("⏳ 开始批量Embedding（云服务API模式：高并发+大批次）...")
            print(f"   总数据量: {len(enriched_chunks)} 条")
            print(f"   批处理大小: 100条/批（平衡模式）")
            print(f"   执行方式: 高并发执行 (并发数: 10)")
            print(f"   批次间延迟: 1.0秒（避免触发速率限制）")
            batch_size = 100
            max_workers = 10
            request_delay = 1.0
        
        embedded_chunks = embedding_client.embed_chunks(
            enriched_chunks,
            batch_size=batch_size,
            max_workers=max_workers,
            request_delay=request_delay
        )
    
    actual_dim = len(embedded_chunks[0]['vector'])
    print(f"✅ Embedding完成:")
    print(f"   - 向量数量: {len(embedded_chunks)}")
    print(f"   - 向量维度: {actual_dim}")
    
        # 保存Embedding结果到缓存
        save_to_cache(embedded_chunks, cache_key, "embeddings")
    else:
        print("📂 从缓存加载Embedding结果...")
        actual_dim = len(embedded_chunks[0]['vector'])
        print(f"✅ Embedding加载完成:")
        print(f"   - 向量数量: {len(embedded_chunks)}")
        print(f"   - 向量维度: {actual_dim}")
    
    # ========== 步骤1.5: 存储到Milvus ==========
    print("\n[1.5] 存储到Milvus...")
    
    try:
        with MilvusClient() as client:
            # 检查Collection是否已存在
            collection_name = os.getenv("MILVUS_COLLECTION_NAME", "parliament_speeches")
            from pymilvus import utility
            
            if utility.has_collection(collection_name):
                if force_rebuild:
                    print(f"🔄 强制重建模式：删除现有Collection '{collection_name}'...")
                    utility.drop_collection(collection_name)
                else:
                    print(f"⚠️  Collection '{collection_name}' 已存在")
                    try:
                        recreate = input("是否重新创建？(y/n，默认n): ").strip().lower()
                    except EOFError:
                        # 非交互模式下默认不重新创建
                        recreate = 'n'
                        print("n (非交互模式，自动选择)")
                    
                    if recreate == 'y':
                utility.drop_collection(collection_name)
                    else:
                        print("⏭️  跳过Milvus创建，使用现有Collection")
                        
                        # 获取现有数据统计
                        stats_cache = load_from_cache(cache_key, "data_stats")
                        if stats_cache:
                            speeches_count = stats_cache['speeches_count']
                            chunks_count = stats_cache['chunks_count']
                        else:
                            speeches_count = 0
                            chunks_count = len(enriched_chunks)
                        
                        from pymilvus import Collection
                        collection = Collection(collection_name)
                        return speeches_count, chunks_count, collection.num_entities
            
            # 创建Collection Manager
            manager = MilvusCollectionManager()
            
            # 创建Collection（传入实际维度）
            manager.create_collection(dimension=actual_dim)
            
            # 插入数据（分批插入，避免gRPC消息大小限制）
            print("⏳ 插入数据到Milvus（分批插入）...")
            print(f"   总数据量: {len(embedded_chunks)} 条")
            print(f"   分批大小: 5000条/批（避免gRPC消息大小限制）")
            manager.insert_data(embedded_chunks, batch_size=5000)
            
            # 创建索引
            print("⏳ 创建索引...")
            manager.create_index()
            
            # 加载到内存
            print("⏳ 加载Collection到内存...")
            manager.collection.load()
            
            # 验证
            count = manager.collection.num_entities
            print(f"✅ 索引构建完成:")
            print(f"   - Collection名称: {collection_name}")
            print(f"   - 向量数量: {count}")
            
            # 获取统计信息
            stats_cache = load_from_cache(cache_key, "data_stats")
            if stats_cache:
                speeches_count = stats_cache['speeches_count']
                chunks_count = stats_cache['chunks_count']
            else:
                speeches_count = 0
                chunks_count = len(enriched_chunks)
            
            return speeches_count, chunks_count, count
            
    except Exception as e:
        logger.error(f"❌ Milvus操作失败: {e}")
        print("\n请检查:")
        print("  1. Milvus服务是否已启动")
        print("  2. Milvus连接配置是否正确（.env文件）")
        raise


def test_workflow(questions: list):
    """
    测试完整工作流
    
    Args:
        questions: 测试问题列表
    """
    print("\n" + "="*80)
    print("🚀 步骤2: 运行完整工作流测试")
    print("="*80)
    
    # 初始化工作流
    print("\n[2.1] 初始化工作流...")
    try:
        workflow = QuestionAnswerWorkflow()
        print("✅ 工作流初始化成功")
    except Exception as e:
        logger.error(f"❌ 工作流初始化失败: {e}")
        raise
    
    # 测试每个问题
    results = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"测试问题 {i}/{len(questions)}")
        print(f"{'='*80}")
        print(f"\n问题: {question}")
        print(f"\n开始处理...")
        
        try:
            # 运行工作流（直接传递问题字符串）
            final_state = workflow.run(question)
            
            # 检查结果
            if final_state.get("error"):
                print(f"\n❌ 处理失败:")
                print(f"   错误类型: {final_state.get('error_type', 'UNKNOWN')}")
                print(f"   错误信息: {final_state.get('error', 'N/A')}")
                results.append({
                    "question": question,
                    "success": False,
                    "error": final_state.get("error"),
                    "error_type": final_state.get("error_type")
                })
            else:
                final_answer = final_state.get("final_answer", "")
                intent = final_state.get("intent", "unknown")
                question_type = final_state.get("question_type", "unknown")
                
                print(f"\n✅ 处理成功:")
                print(f"   意图: {intent}")
                print(f"   问题类型: {question_type}")
                print(f"   答案长度: {len(final_answer)} 字符")
                print(f"\n答案预览:")
                print("-" * 80)
                # 显示前500字符
                preview = final_answer[:500] + "..." if len(final_answer) > 500 else final_answer
                print(preview)
                print("-" * 80)
                
                results.append({
                    "question": question,
                    "success": True,
                    "intent": intent,
                    "question_type": question_type,
                    "answer_length": len(final_answer),
                    "answer_preview": preview
                })
        
        except Exception as e:
            logger.error(f"❌ 测试问题失败: {e}", exc_info=True)
            results.append({
                "question": question,
                "success": False,
                "error": str(e)
            })
    
    # 汇总结果
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    passed = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"\n{status} - 问题 {i}: {result['question'][:60]}...")
        
        if result.get("success"):
            print(f"   意图: {result.get('intent')}")
            print(f"   类型: {result.get('question_type')}")
            print(f"   答案长度: {result.get('answer_length')} 字符")
        else:
            print(f"   错误: {result.get('error', 'N/A')}")
    
    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    return results


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🧪 端到端真实环境测试 - 智能断点模式")
    print("="*80)
    print("\n【测试目标】")
    print("1. 加载2018-2020年的真实数据（支持缓存）")
    print("2. 构建Milvus向量索引（支持断点续传）")
    print("3. 运行完整工作流")
    print("4. 验证输出质量")
    
    print("\n【环境变量控制】")
    print("- FORCE_REBUILD=true    # 强制重建所有步骤")
    print("- SKIP_INDEX_BUILD=true # 跳过索引构建，直接测试工作流")
    print("- SKIP_WORKFLOW=true    # 只构建索引，跳过工作流测试")
    
    # 获取控制选项
    force_rebuild = os.getenv("FORCE_REBUILD", "").lower() == "true"
    skip_index_build = os.getenv("SKIP_INDEX_BUILD", "").lower() == "true"
    skip_workflow = os.getenv("SKIP_WORKFLOW", "").lower() == "true"
    
    if force_rebuild:
        print("🔄 强制重建模式：将重新构建所有步骤")
    if skip_index_build:
        print("⏭️  跳过索引构建模式：直接运行工作流测试")
    if skip_workflow:
        print("🏗️  只构建索引模式：跳过工作流测试")
    
    print("\n【前置条件检查】")
    print("检查Milvus连接...")
    
    # 确保使用Milvus Lite模式
    if os.getenv("MILVUS_MODE") != "lite":
        print("⚠️  检测到MILVUS_MODE不是lite，设置为lite模式...")
        os.environ["MILVUS_MODE"] = "lite"
        print("✅ 已设置MILVUS_MODE=lite")
    
    try:
        with MilvusClient() as client:
            print("✅ Milvus Lite连接成功")
            print(f"   模式: {client.mode}")
            print(f"   数据路径: {os.getenv('MILVUS_LITE_PATH', './milvus_data/milvus_lite.db')}")
    except Exception as e:
        print(f"❌ Milvus连接失败: {e}")
        print("\n请确保:")
        print("  1. 已安装milvus-lite: pip install milvus-lite")
        print("  2. .env文件中MILVUS_MODE设置为lite（或会在运行时自动设置）")
        return 1
    
    print("检查第三方LLM API配置...")
    llm_available = False
    try:
        from src.llm.client import GeminiLLMClient
        llm = GeminiLLMClient()
        test_response = llm.invoke("测试")
        print("✅ 第三方LLM API连接成功")
        llm_available = True
    except Exception as e:
        print(f"⚠️  第三方LLM API连接失败: {e}")
        print("\n提示:")
        print("  1. 如果只测试 embedding 构建索引，可以继续运行")
        print("  2. 如果要测试完整工作流，需要配置:")
        print("     - .env文件中配置OPENAI_API_KEY（作为第三方代理密钥）")
        print("     - .env文件中配置THIRD_PARTY_BASE_URL")
        print("     - 确保网络连接正常")
        print("\n继续运行 embedding 测试...")
        
        # 如果用户只想测试 embedding，可以继续
        try:
            user_input = input("\n是否继续只测试 embedding？（y/n，默认y）: ").strip().lower()
        except EOFError:
            # 非交互模式下默认继续测试
            user_input = 'y'
            print("y (非交互模式，自动选择)")
            
        if user_input and user_input != 'y':
            print("已取消测试")
        return 1
    
    # ========== 步骤1: 构建索引 ==========
    speeches_count = chunks_count = vectors_count = 0
    
    if not skip_index_build:
    try:
        # 设置要处理的年份范围（可以修改这里来改变处理的数据范围）
        # 格式：年份列表，例如 ['2018', '2019', '2020'] 或 ['2021'] 或 ['2015', '2016', '2017', '2018', '2019', '2020']
        # years = ['2018', '2019', '2020']  # 👈 在这里修改年份范围
        years = ['2018'] # 先用2018年的数据处理，测试整个流程，后续可以扩展。
            
            speeches_count, chunks_count, vectors_count = build_index_for_years(years, force_rebuild=force_rebuild)
        
        print("\n" + "="*80)
        print("✅ 索引构建完成！")
        print("="*80)
        print(f"📊 统计信息:")
        print(f"   - 演讲记录: {speeches_count} 条")
        print(f"   - 文本块: {chunks_count} 个")
        print(f"   - 向量数量: {vectors_count} 个")
        
    except Exception as e:
        error_msg = str(e)
        # 避免格式化错误（如果错误消息包含特殊字符）
        logger.error(f"❌ 索引构建失败: {error_msg}")
        logger.exception("详细错误信息:")
        return 1
    else:
        print("\n" + "="*80)
        print("⏭️  跳过索引构建步骤")
        print("="*80)
        
        # 检查现有索引状态
        milvus_status = check_milvus_collection_status()
        if milvus_status["exists"] and milvus_status["count"] > 0:
            vectors_count = milvus_status["count"]
            print(f"✅ 发现现有索引: {vectors_count} 个向量")
        else:
            print("⚠️  未发现现有索引，工作流测试可能失败")
            
        if skip_workflow:
            print("✅ 只执行索引检查，测试完成")
            return 0
    
    # ========== 步骤2: 测试工作流 ==========
    if skip_workflow:
        print("\n" + "="*80)
        print("⏭️  跳过工作流测试（用户设置）")
        print("="*80)
        print("\n✅ 索引构建测试完成！")
        return 0
    
    # 只有在 LLM 可用时才测试工作流
    if not llm_available:
        print("\n" + "="*80)
        print("⚠️  跳过工作流测试（LLM API 未配置）")
        print("="*80)
        print("\n✅ Embedding 索引构建测试完成！")
        print("提示：配置 OPENAI_API_KEY 后可以运行完整工作流测试")
        return 0
    
    # 定义测试问题
    test_questions = [
        # 简单问题
        "2019年德国议会讨论了哪些主要议题？",
        "2020年绿党在气候保护方面的主要观点是什么？",
        
        # 复杂问题 - 变化类
        "在2018-2020年期间，CDU/CSU在难民政策上的立场有何变化？",
        
        # 复杂问题 - 对比类
        "对比CDU/CSU、SPD和绿党在2019年数字化政策上的立场差异",
        
        # 复杂问题 - 总结类
        "请总结2018-2020年期间，德国议会在气候保护方面的主要讨论",
    ]
    
    try:
        results = test_workflow(test_questions)
        
        # 最终总结
        print("\n" + "="*80)
        print("🎉 端到端测试完成！")
        print("="*80)
        
        passed = sum(1 for r in results if r.get("success", False))
        total = len(results)
        
        if passed == total:
            print("\n✅ 所有测试通过！系统运行正常。")
            return 0
        else:
            print(f"\n⚠️  {total - passed} 个测试失败，请检查日志。")
            return 1
            
    except Exception as e:
        logger.error(f"❌ 工作流测试失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

