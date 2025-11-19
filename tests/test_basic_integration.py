"""
基础集成测试
测试模块导入和基本功能（不需要LLM服务）
"""

import sys
import os

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_imports():
    """测试所有模块能否正常导入"""
    print("\n【测试1: 模块导入】")
    
    try:
        # 基础模块
        from src.graph.state import create_initial_state, update_state
        print("✅ state模块导入成功")
        
        # 增强版节点
        from src.graph.nodes.intent_enhanced import EnhancedIntentNode
        print("✅ EnhancedIntentNode导入成功")
        
        from src.graph.nodes.exception_enhanced import EnhancedExceptionNode
        print("✅ EnhancedExceptionNode导入成功")
        
        # Prompt模块
        from src.llm.prompts import PromptTemplates
        print("✅ PromptTemplates导入成功")
        
        from src.llm.prompts_fallback import FallbackPrompts
        print("✅ FallbackPrompts导入成功")
        
        # 工具模块
        from src.utils.language_detect import detect_language, get_system_capabilities
        print("✅ language_detect模块导入成功")
        
        # 工作流
        from src.graph.workflow import QuestionAnswerWorkflow
        print("✅ QuestionAnswerWorkflow导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_state_creation():
    """测试状态创建"""
    print("\n【测试2: 状态创建】")
    
    try:
        from src.graph.state import create_initial_state, update_state
        
        # 创建初始状态
        question = "测试问题"
        state = create_initial_state(question)
        
        assert state["question"] == question
        assert state["current_node"] == "start"
        assert state["next_node"] == "intent"
        print("✅ 初始状态创建成功")
        
        # 更新状态
        updated_state = update_state(
            state,
            intent="simple",
            current_node="intent",
            next_node="extract"
        )
        
        assert updated_state["intent"] == "simple"
        assert updated_state["current_node"] == "intent"
        assert updated_state["next_node"] == "extract"
        print("✅ 状态更新成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_language_detection():
    """测试语言检测"""
    print("\n【测试3: 语言检测】")
    
    try:
        from src.utils.language_detect import detect_language
        
        test_cases = [
            ("你会做什么？", "zh"),
            ("Was können Sie tun?", "de"),
            ("2019年德国议会讨论了哪些议题？", "zh"),
            ("Welche Themen wurden 2019 diskutiert?", "de"),
        ]
        
        passed = 0
        for text, expected in test_cases:
            detected = detect_language(text)
            if detected == expected:
                print(f"  ✅ '{text[:30]}...' → {detected}")
                passed += 1
            else:
                print(f"  ❌ '{text[:30]}...' → {detected} (期望: {expected})")
        
        print(f"✅ 语言检测测试: {passed}/{len(test_cases)} 通过")
        return passed == len(test_cases)
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_templates():
    """测试Prompt模板"""
    print("\n【测试4: Prompt模板】")
    
    try:
        from src.llm.prompts import PromptTemplates
        from src.llm.prompts_fallback import FallbackPrompts
        
        # 测试正常流程Prompts
        prompts = PromptTemplates()
        
        question = "2019年德国议会讨论了什么？"
        
        intent_prompt = prompts.format_intent_prompt(question)
        assert question in intent_prompt
        assert "复杂度" in intent_prompt or "简单" in intent_prompt
        print("  ✅ 意图判断Prompt格式化成功")
        
        classification_prompt = prompts.format_classification_prompt(question)
        assert question in classification_prompt
        print("  ✅ 问题分类Prompt格式化成功")
        
        extraction_prompt = prompts.format_extraction_prompt(question)
        assert question in extraction_prompt
        print("  ✅ 参数提取Prompt格式化成功")
        
        # 测试兜底Prompts
        fallback = FallbackPrompts()
        
        validation_prompt = fallback.format_validation_prompt(question)
        assert question in validation_prompt
        print("  ✅ 合法性检查Prompt格式化成功")
        
        irrelevant_response = fallback.format_irrelevant_response(question)
        assert question in irrelevant_response
        print("  ✅ 不相关问题回复格式化成功")
        
        print("✅ Prompt模板测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_exception_node_basic():
    """测试ExceptionNode基本功能（不调用LLM）"""
    print("\n【测试5: ExceptionNode基本功能】")
    
    try:
        from src.graph.state import create_initial_state, update_state
        from src.graph.nodes.exception_enhanced import EnhancedExceptionNode
        
        # 测试未找到材料
        question = "1900年德国议会讨论了什么？"
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
        
        assert result["next_node"] == "end"
        assert result.get("final_answer") is not None
        assert "1900" in result["final_answer"]
        print("  ✅ NO_MATERIAL异常处理正确")
        
        # 测试LLM错误
        question2 = "2019年CDU的立场？"
        state2 = create_initial_state(question2)
        state2 = update_state(
            state2,
            error="API调用失败",
            error_type="LLM_ERROR"
        )
        
        result2 = node(state2)
        
        assert result2["next_node"] == "end"
        assert result2.get("final_answer") is not None
        assert "语言模型" in result2["final_answer"] or "LLM" in result2["final_answer"]
        print("  ✅ LLM_ERROR异常处理正确")
        
        print("✅ ExceptionNode基本功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("基础集成测试（不需要LLM服务）")
    print("="*60)
    
    tests = [
        ("模块导入", test_imports),
        ("状态创建", test_state_creation),
        ("语言检测", test_language_detection),
        ("Prompt模板", test_prompt_templates),
        ("ExceptionNode基本功能", test_exception_node_basic),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 崩溃: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有基础测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

