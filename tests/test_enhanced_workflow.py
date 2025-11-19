"""
增强版工作流端到端测试
测试问题合法性检查、双语支持、异常处理等新功能

【注意】
部分测试需要LLM服务（Gemini API）和Milvus服务
如果服务未启动，相关测试会被跳过
"""

import sys
import os

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.state import create_initial_state
from src.graph.nodes.intent_enhanced import EnhancedIntentNode
from src.graph.nodes.exception_enhanced import EnhancedExceptionNode
from src.utils.logger import logger


def test_meta_question_chinese():
    """测试1: 元问题（中文）- "你会做什么？" """
    print("\n" + "="*60)
    print("【测试1: 元问题（中文）】")
    print("="*60)
    
    question = "你会做什么？"
    print(f"问题: {question}")
    
    try:
        state = create_initial_state(question)
        node = EnhancedIntentNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"下一节点: {result['next_node']}")
        print(f"错误类型: {result.get('error_type', 'N/A')}")
        
        if result.get('final_answer'):
            print(f"\n回答（前300字符）:")
            print(result['final_answer'][:300])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def test_meta_question_german():
    """测试2: 元问题（德文）- "Was können Sie tun?" """
    print("\n" + "="*60)
    print("【测试2: 元问题（德文）】")
    print("="*60)
    
    question = "Was können Sie tun?"
    print(f"问题: {question}")
    
    try:
        state = create_initial_state(question)
        node = EnhancedIntentNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"下一节点: {result['next_node']}")
        print(f"语言: {result.get('language', 'N/A')}")
        print(f"错误类型: {result.get('error_type', 'N/A')}")
        
        if result.get('final_answer'):
            print(f"\n回答（前300字符）:")
            print(result['final_answer'][:300])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def test_irrelevant_question():
    """测试3: 不相关问题 """
    print("\n" + "="*60)
    print("【测试3: 不相关问题】")
    print("="*60)
    
    question = "今天天气怎么样？"
    print(f"问题: {question}")
    
    try:
        state = create_initial_state(question)
        node = EnhancedIntentNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"下一节点: {result['next_node']}")
        print(f"错误类型: {result.get('error_type', 'N/A')}")
        
        if result.get('final_answer'):
            print(f"\n回答（前300字符）:")
            print(result['final_answer'][:300])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def test_simple_question_chinese():
    """测试4: 正常简单问题（中文）"""
    print("\n" + "="*60)
    print("【测试4: 正常简单问题（中文）】")
    print("="*60)
    
    question = "2019年德国议会讨论了哪些主要议题？"
    print(f"问题: {question}")
    
    try:
        state = create_initial_state(question)
        node = EnhancedIntentNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"意图: {result.get('intent', 'N/A')}")
        print(f"下一节点: {result['next_node']}")
        
        if result.get('complexity_analysis'):
            print(f"\n复杂度分析（前200字符）:")
            print(result['complexity_analysis'][:200])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def test_simple_question_german():
    """测试5: 正常简单问题（德文）"""
    print("\n" + "="*60)
    print("【测试5: 正常简单问题（德文）】")
    print("="*60)
    
    question = "Welche Hauptthemen wurden 2019 im Bundestag diskutiert?"
    print(f"问题: {question}")
    
    try:
        state = create_initial_state(question)
        node = EnhancedIntentNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"意图: {result.get('intent', 'N/A')}")
        print(f"下一节点: {result['next_node']}")
        
        if result.get('complexity_analysis'):
            print(f"\n复杂度分析（前200字符）:")
            print(result['complexity_analysis'][:200])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def test_complex_question():
    """测试6: 正常复杂问题"""
    print("\n" + "="*60)
    print("【测试6: 正常复杂问题】")
    print("="*60)
    
    question = "在2015-2018年期间，不同党派在难民政策上的立场有何变化？"
    print(f"问题: {question}")
    
    try:
        state = create_initial_state(question)
        node = EnhancedIntentNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"意图: {result.get('intent', 'N/A')}")
        print(f"下一节点: {result['next_node']}")
        
        if result.get('complexity_analysis'):
            print(f"\n复杂度分析（前200字符）:")
            print(result['complexity_analysis'][:200])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def test_exception_no_material():
    """测试7: 异常处理 - 未找到材料"""
    print("\n" + "="*60)
    print("【测试7: 异常处理 - 未找到材料】")
    print("="*60)
    
    question = "1900年德国议会讨论了什么？"
    print(f"问题: {question}")
    
    try:
        from src.graph.state import update_state
        
        state = create_initial_state(question)
        state = update_state(
            state,
            error="未找到相关材料",
            error_type="NO_MATERIAL",
            parameters={
                "time_range": {"start_year": "1900"},
                "topics": ["议会讨论"]
            }
        )
        
        node = EnhancedExceptionNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"下一节点: {result['next_node']}")
        
        if result.get('final_answer'):
            print(f"\n回答（前300字符）:")
            print(result['final_answer'][:300])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def test_exception_llm_error():
    """测试8: 异常处理 - LLM错误"""
    print("\n" + "="*60)
    print("【测试8: 异常处理 - LLM错误】")
    print("="*60)
    
    question = "2019年CDU的立场是什么？"
    print(f"问题: {question}")
    
    try:
        from src.graph.state import update_state
        
        state = create_initial_state(question)
        state = update_state(
            state,
            error="Gemini API rate limit exceeded",
            error_type="LLM_ERROR"
        )
        
        node = EnhancedExceptionNode()
        result = node(state)
        
        print(f"✅ 处理成功")
        print(f"下一节点: {result['next_node']}")
        
        if result.get('final_answer'):
            print(f"\n回答（前300字符）:")
            print(result['final_answer'][:300])
            print("...\n")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("增强版工作流端到端测试")
    print("="*60)
    print("\n【注意】")
    print("- 测试1-3: 不需要LLM，测试合法性检查逻辑")
    print("- 测试4-6: 需要LLM，测试意图判断")
    print("- 测试7-8: 不需要LLM，测试异常处理")
    print()
    
    results = []
    
    # 不需要LLM的测试（合法性检查）
    print("\n【第一组: 合法性检查测试（需要LLM）】")
    results.append(("元问题（中文）", test_meta_question_chinese()))
    results.append(("元问题（德文）", test_meta_question_german()))
    results.append(("不相关问题", test_irrelevant_question()))
    
    # 需要LLM的测试（意图判断）
    print("\n【第二组: 意图判断测试（需要LLM）】")
    results.append(("简单问题（中文）", test_simple_question_chinese()))
    results.append(("简单问题（德文）", test_simple_question_german()))
    results.append(("复杂问题", test_complex_question()))
    
    # 不需要LLM的测试（异常处理）
    print("\n【第三组: 异常处理测试（不需要LLM）】")
    results.append(("未找到材料", test_exception_no_material()))
    results.append(("LLM错误", test_exception_llm_error()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

