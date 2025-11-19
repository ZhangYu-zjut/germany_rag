"""
调试意图判断 - 查看LLM原始响应
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm.client import GeminiLLMClient
from src.llm.prompts import PromptTemplates

print("="*80)
print("意图判断调试 - 查看LLM原始响应")
print("="*80)

# 初始化
client = GeminiLLMClient()
prompts = PromptTemplates()

# 测试用例
test_cases = [
    {
        "question": "2019年德国议会讨论了哪些主要议题？",
        "expected": "simple"
    },
    {
        "question": "2021年绿党在气候保护方面的主要观点是什么？",
        "expected": "simple"
    },
]

for i, test_case in enumerate(test_cases, 1):
    question = test_case["question"]
    expected = test_case["expected"]
    
    print(f"\n{'='*80}")
    print(f"【测试用例 {i}】")
    print(f"{'='*80}")
    print(f"问题: {question}")
    print(f"预期: {expected}")
    
    # 构建Prompt
    prompt = prompts.format_intent_prompt(question)
    
    print(f"\n【发送给LLM的Prompt】")
    print("-"*80)
    print(prompt)
    print("-"*80)
    
    # 调用LLM
    print(f"\n🔄 调用LLM...")
    try:
        response = client.invoke(prompt)
        
        print(f"\n【LLM原始响应】")
        print("-"*80)
        print(response)
        print("-"*80)
        
        # 解析响应
        response_lower = response.lower()
        
        has_complex = "复杂" in response or "complex" in response_lower
        has_simple = "简单" in response or "simple" in response_lower
        
        print(f"\n【解析结果】")
        print(f"  包含'复杂': {has_complex}")
        print(f"  包含'简单': {has_simple}")
        
        if has_complex:
            intent = "complex"
        elif has_simple:
            intent = "simple"
        else:
            # 关键词匹配
            complex_keywords = ["时间跨度", "多个对象", "对比", "趋势", "变化", "分析"]
            has_keywords = any(kw in response for kw in complex_keywords)
            intent = "complex" if has_keywords else "simple"
            print(f"  关键词匹配: {has_keywords}")
        
        print(f"\n  最终判断: {intent}")
        print(f"  预期判断: {expected}")
        print(f"  结果: {'✅ 通过' if intent == expected else '❌ 失败'}")
        
        # 分析原因
        if intent != expected:
            print(f"\n【失败原因分析】")
            if "主要议题" in question or "主要观点" in question:
                print("  ⚠️  问题包含'主要议题'或'主要观点'")
                if "总结" in response or "综合分析" in response:
                    print("  ⚠️  LLM响应中包含'总结'或'综合分析'")
                    print("  💡 建议: 需要更明确地告诉LLM这类问题属于简单问题")
            
            # 查找响应中的关键词
            print(f"\n  响应中的关键词:")
            keywords_to_check = ["总结", "综合", "分析", "主要", "议题", "观点"]
            for kw in keywords_to_check:
                if kw in response:
                    print(f"    - '{kw}': 出现在响应中")
        
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("调试完成")
print("="*80)

