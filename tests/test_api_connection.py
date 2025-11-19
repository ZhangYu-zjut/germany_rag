"""
快速验证第三方API连接
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("="*60)
print("第三方API连接测试")
print("="*60)

# 步骤1: 检查环境变量
print("\n【步骤1: 检查环境变量】")
try:
    from src.config.settings import settings
    
    print(f"✅ 配置加载成功")
    print(f"   - API Base URL: {settings.third_party_base_url}")
    print(f"   - 模型名称: {settings.third_party_model_name}")
    print(f"   - API Key: {'已配置' if settings.openai_api_key else '❌ 未配置'}")
    
    if not settings.openai_api_key:
        print("\n❌ 错误: OPENAI_API_KEY未配置")
        print("请在.env文件中添加: OPENAI_API_KEY=your_key_here")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    sys.exit(1)

# 步骤2: 初始化LLM客户端
print("\n【步骤2: 初始化LLM客户端】")
try:
    from src.llm.client import GeminiLLMClient
    
    client = GeminiLLMClient()
    print(f"✅ LLM客户端初始化成功")
    
except Exception as e:
    print(f"❌ LLM客户端初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 步骤3: 测试API连接
print("\n【步骤3: 测试API连接】")
try:
    print("🔄 发送测试请求...")
    response = client.invoke("请用一句话介绍你自己。")
    
    print(f"✅ API调用成功！")
    print(f"\n回复内容:")
    print(f"   {response}")
    print()
    
except Exception as e:
    print(f"❌ API调用失败: {e}")
    print("\n可能的原因:")
    print("  1. API Key不正确")
    print("  2. 网络连接问题")
    print("  3. API端点不可用")
    print("  4. 模型名称错误")
    print("\n请检查.env文件中的配置:")
    print("  OPENAI_API_KEY=your_key_here")
    print(f"  THIRD_PARTY_BASE_URL={settings.third_party_base_url}")
    print(f"  THIRD_PARTY_MODEL_NAME={settings.third_party_model_name}")
    
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("="*60)
print("✅ 所有测试通过！第三方API连接正常！")
print("="*60)
print("\n现在可以运行完整测试:")
print("  python tests/test_real_llm.py")
print()

