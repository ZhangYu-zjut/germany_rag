"""
详细调试意图判断 - 查看LLM完整响应和解析过程
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm.client import GeminiLLMClient
from src.llm.prompts import PromptTemplates
from src.graph.nodes.intent_enhanced import EnhancedIntentNode
from src.graph.state import create_initial_state

print("="*80)
print("详细调试 - 查看LLM完整响应和解析过程")
print("="*80)

# 初始化
client = GeminiLLMClient()
prompts = PromptTemplates()

# 错误用例
error_cases = [
    {
        "question": "2019年德国议会讨论了哪些主要议题？",
        "expected": "simple"
    },
    {
        "question": "2021年绿党在气候保护方面的主要观点是什么？",
        "expected": "simple"
    },
]

for i, test_case in enumerate(error_cases, 1):
    question = test_case["question"]
    expected = test_case["expected"]
    
    print(f"\n{'='*80}")
    print(f"【错误用例 {i} - 完整调试】")
    print(f"{'='*80}")
    print(f"问题: {question}")
    print(f"预期: {expected}")
    
    # 步骤1: 查看发送给LLM的Prompt
    print(f"\n【步骤1: 发送给LLM的Prompt】")
    print("-"*80)
    prompt = prompts.format_intent_prompt(question)
    print(prompt)
    print("-"*80)
    
    # 步骤2: 调用LLM获取原始响应
    print(f"\n【步骤2: LLM原始响应】")
    print("-"*80)
    try:
        raw_response = client.invoke(prompt)
        print(raw_response)
        print("-"*80)
        
        # 步骤3: 分析响应内容
        print(f"\n【步骤3: 响应内容分析】")
        response_lower = raw_response.lower()
        
        # 查找关键信息
        has_complexity_line = "复杂度:" in raw_response
        has_simple = "简单" in raw_response or "simple" in response_lower
        has_complex = "复杂" in raw_response or "complex" in response_lower
        
        print(f"  包含'复杂度:'行: {has_complexity_line}")
        print(f"  包含'简单': {has_simple}")
        print(f"  包含'复杂': {has_complex}")
        
        # 查找复杂关键词
        complex_keywords = ["时间跨度", "多个对象", "多个党派", "不同党派", "对比", "趋势", "变化", "演变", "差异", "异同"]
        found_complex_keywords = [kw for kw in complex_keywords if kw in raw_response]
        print(f"  发现的复杂关键词: {found_complex_keywords}")
        
        # 查找简单指示词
        simple_indicators = ["单一时间点", "单一对象", "单一党派", "事实查询", "观点总结"]
        found_simple_indicators = [ind for ind in simple_indicators if ind in raw_response]
        print(f"  发现的简单指示词: {found_simple_indicators}")
        
        # 步骤4: 使用实际解析逻辑
        print(f"\n【步骤4: 使用实际解析逻辑】")
        from src.graph.nodes.intent_enhanced import EnhancedIntentNode
        node = EnhancedIntentNode()
        
        # 手动调用解析方法
        parsed_intent, analysis = node._parse_intent_response(raw_response)
        print(f"  解析结果: {parsed_intent}")
        print(f"  分析内容: {analysis[:200]}...")
        
        # 步骤5: 完整流程测试
        print(f"\n【步骤5: 完整流程测试】")
        state = create_initial_state(question)
        result_state = node(state)
        final_intent = result_state.get("intent")
        print(f"  最终意图: {final_intent}")
        print(f"  预期意图: {expected}")
        print(f"  结果: {'✅ 通过' if final_intent == expected else '❌ 失败'}")
        
        # 步骤6: 问题诊断
        if final_intent != expected:
            print(f"\n【步骤6: 问题诊断】")
            print(f"  ❌ 判断错误！")
            
            # 分析原因
            if has_complexity_line:
                # 提取复杂度行的内容
                for line in raw_response.split('\n'):
                    if "复杂度:" in line:
                        print(f"  '复杂度:'行的内容: {line}")
                        if "复杂" in line:
                            print(f"  ⚠️  问题: LLM在'复杂度:'行中写了'复杂'")
                            print(f"  💡 可能原因: Prompt没有成功引导LLM")
                        break
            
            if not has_complexity_line:
                print(f"  ⚠️  问题: LLM没有按照格式输出'复杂度:'行")
                print(f"  💡 可能原因: LLM没有遵循Prompt格式要求")
            
            if has_complex and not has_simple:
                print(f"  ⚠️  问题: LLM明确判断为'复杂'")
                print(f"  💡 需要: 分析为什么LLM认为这是复杂问题")
                # 查找LLM的理由
                if "理由:" in raw_response:
                    for line in raw_response.split('\n'):
                        if "理由:" in line:
                            print(f"  LLM的理由: {line}")
                            break
            
            # 检查是否有误解
            if "主要议题" in question or "主要观点" in question:
                if "总结" in raw_response or "综合分析" in raw_response:
                    print(f"  ⚠️  关键发现: LLM在响应中提到了'总结'或'综合分析'")
                    print(f"  💡 这说明LLM仍然认为'主要议题/主要观点'需要总结")
                    print(f"  💡 需要在Prompt中更强烈地纠正这个误解")
        
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("调试完成 - 请查看上述详细信息找出问题")
print("="*80)


