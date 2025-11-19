"""
环境检查脚本
运行main.py前的环境验证
"""

import sys
import os


def check_environment():
    """检查系统环境"""
    print("="*80)
    print("德国议会智能问答系统 - 环境检查")
    print("="*80)
    
    checks = []
    errors = []
    
    # 1. 检查.env文件
    print("\n[1/7] 检查.env文件...")
    if os.path.exists('.env'):
        checks.append("✅ .env文件存在")
        
        # 读取关键配置
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'OPENAI_API_KEY' in content and 'your_api_key_here' not in content:
                checks.append("✅ API Key已配置")
            else:
                errors.append("❌ API Key未配置或使用默认值")
    else:
        errors.append("❌ .env文件不存在")
    
    # 2. 检查数据目录
    print("[2/7] 检查数据目录...")
    data_dir = 'data/pp_json_49-21'
    if os.path.exists(data_dir):
        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        if json_files:
            checks.append(f"✅ 数据目录存在 (包含{len(json_files)}个JSON文件)")
        else:
            errors.append(f"❌ 数据目录存在但没有JSON文件")
    else:
        errors.append("❌ 数据目录不存在")
    
    # 3. 检查Python依赖
    print("[3/7] 检查Python依赖...")
    required_packages = [
        'pymilvus',
        'langchain',
        'langgraph',
        'openai',
        'loguru',
        'pydantic',
        
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if not missing_packages:
        checks.append(f"✅ 所有依赖包已安装 ({len(required_packages)}个)")
    else:
        errors.append(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
    
    # 4. 检查Milvus连接
    print("[4/7] 检查Milvus连接...")
    try:
        from src.vectordb import MilvusClient
        with MilvusClient() as client:
            checks.append("✅ Milvus连接成功")
    except Exception as e:
        errors.append(f"❌ Milvus连接失败: {str(e)[:50]}...")
    
    # 5. 检查LLM客户端
    print("[5/7] 检查LLM客户端...")
    try:
        from src.llm import GeminiLLMClient
        client = GeminiLLMClient()
        checks.append("✅ LLM客户端初始化成功")
    except Exception as e:
        errors.append(f"❌ LLM初始化失败: {str(e)[:50]}...")
    
    # 6. 检查Collection
    print("[6/7] 检查Milvus Collection...")
    try:
        from src.vectordb import MilvusCollectionManager
        manager = MilvusCollectionManager()
        # 尝试加载collection
        manager.collection.load()
        num_entities = manager.collection.num_entities
        checks.append(f"✅ Collection存在 (包含{num_entities}条记录)")
    except Exception as e:
        errors.append(f"❌ Collection不存在或无法访问: {str(e)[:50]}...")
    
    # 7. 检查日志目录
    print("[7/7] 检查日志目录...")
    if not os.path.exists('logs'):
        try:
            os.makedirs('logs')
            checks.append("✅ 日志目录已创建")
        except Exception as e:
            errors.append(f"❌ 无法创建日志目录: {str(e)}")
    else:
        checks.append("✅ 日志目录存在")
    
    # 打印结果
    print("\n" + "="*80)
    print("检查结果:")
    print("="*80)
    
    if checks:
        print("\n✅ 成功项:")
        for check in checks:
            print(f"  {check}")
    
    if errors:
        print("\n❌ 失败项:")
        for error in errors:
            print(f"  {error}")
    
    print("\n" + "="*80)
    
    # 判断是否可以运行
    if not errors:
        print("✅ 所有检查通过,可以运行系统!")
        print("\n运行命令:")
        print("  python main.py")
        return True
    else:
        print(f"❌ {len(errors)}项检查失败,请先解决以下问题:\n")
        
        # 提供解决建议
        if any("Milvus连接失败" in e for e in errors):
            print("🔧 Milvus连接失败解决方案:")
            print("  1. 检查Docker是否运行: docker ps")
            print("  2. 启动Milvus: docker start milvus")
            print("  3. 或创建新容器: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest")
            print()
        
        if any("Collection不存在" in e for e in errors):
            print("🔧 Collection不存在解决方案:")
            print("  运行索引构建脚本: python build_index.py")
            print()
        
        if any("API Key" in e for e in errors):
            print("🔧 API Key问题解决方案:")
            print("  编辑.env文件,设置正确的OPENAI_API_KEY")
            print()
        
        if any("依赖包" in e for e in errors):
            print("🔧 依赖包问题解决方案:")
            print("  安装依赖: pip install -r requirements.txt")
            print()
        
        if any("数据目录" in e for e in errors):
            print("🔧 数据目录问题解决方案:")
            print("  确保data/pp_json_49-21/目录存在并包含JSON文件")
            print()
        
        print("详细故障排查请参考: docs/故障排查指南.md")
        return False


if __name__ == "__main__":
    try:
        success = check_environment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 环境检查过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
