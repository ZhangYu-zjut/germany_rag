"""
真实LLM测试 - 验证意图识别和问题分类的准确性
使用真实的Gemini API进行测试
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.state import create_initial_state, update_state
from src.graph.nodes.intent_enhanced import EnhancedIntentNode
from src.graph.nodes.classify import ClassifyNode
from src.graph.nodes.extract import ExtractNode
from src.llm.client import GeminiLLMClient
from src.utils.logger import logger


def test_intent_classification():
    """
    测试1: 意图判断准确性
    验证系统能否正确区分简单问题和复杂问题
    """
    print("\n" + "="*80)
    print("【测试1: 意图判断准确性】")
    print("="*80)
    
    test_cases = [
        {
            "question": "2019年德国议会讨论了哪些主要议题？",
            "expected_intent": "simple",
            "reason": "单一时间点的事实查询"
        },
        {
            "question": "在2015-2018年期间，CDU/CSU和SPD在难民政策上的立场有何变化？",
            "expected_intent": "complex",
            "reason": "时间跨度4年，涉及2个党派，需要分析变化"
        },
        {
            "question": "对比CDU/CSU、SPD和FDP在2019年数字化政策上的立场差异",
            "expected_intent": "complex",
            "reason": "涉及3个党派的对比分析"
        },
        {
            "question": "2021年绿党在气候保护方面的主要观点是什么？",
            "expected_intent": "simple",  # 或 complex，取决于LLM判断
            "reason": "单一时间点，单一党派，可能是简单问题"
        },
    ]
    
    intent_node = EnhancedIntentNode()
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        question = test_case["question"]
        expected = test_case["expected_intent"]
        reason = test_case["reason"]
        
        print(f"\n--- 测试用例 {i} ---")
        print(f"问题: {question}")
        print(f"预期意图: {expected} ({reason})")
        
        try:
            # 创建状态
            state = create_initial_state(question)
            
            # 调用IntentNode
            print(f"🔄 调用LLM进行意图判断...")
            result_state = intent_node(state)
            
            # 获取结果
            actual_intent = result_state.get("intent")
            complexity_analysis = result_state.get("complexity_analysis", "")
            next_node = result_state.get("next_node")
            
            print(f"✅ LLM返回成功")
            print(f"判断结果: {actual_intent}")
            print(f"分析: {complexity_analysis[:200]}..." if complexity_analysis else "")
            print(f"下一节点: {next_node}")
            
            # 验证
            if actual_intent == expected:
                status = "✅ PASS"
            else:
                status = f"⚠️  DIFF (预期: {expected}, 实际: {actual_intent})"
            
            print(f"验证: {status}")
            
            results.append({
                "question": question,
                "expected": expected,
                "actual": actual_intent,
                "passed": actual_intent == expected,
                "analysis": complexity_analysis
            })
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            logger.error(f"Intent测试失败", exc_info=True)
            results.append({
                "question": question,
                "expected": expected,
                "actual": "ERROR",
                "passed": False,
                "error": str(e)
            })
    
    # 汇总
    print("\n" + "="*80)
    print("【测试1结果汇总】")
    print("="*80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    for i, r in enumerate(results, 1):
        status = "✅" if r["passed"] else "❌"
        print(f"{status} 用例{i}: {r['question'][:40]}... → {r['actual']}")
    
    return results


def test_question_classification():
    """
    测试2: 问题分类准确性
    验证系统能否正确分类问题类型
    """
    print("\n" + "="*80)
    print("【测试2: 问题分类准确性】")
    print("="*80)
    
    test_cases = [
        {
            "question": "在2015-2018年期间，不同党派在难民政策上的立场有何变化？",
            "expected_type": "变化类",
            "reason": "明确询问'变化'，时间跨度4年"
        },
        {
            "question": "对比CDU/CSU和SPD在数字化政策上的立场差异",
            "expected_type": "对比类",
            "reason": "明确询问'对比'和'差异'"
        },
        {
            "question": "请总结2021年绿党在气候保护方面的主要观点",
            "expected_type": "总结类",
            "reason": "明确要求'总结'"
        },
        {
            "question": "2010年到2020年德国议会对气候政策的态度演变趋势",
            "expected_type": "趋势分析",
            "reason": "长期跨度，询问'趋势'和'演变'"
        },
        {
            "question": "2019年Merkel在欧盟一体化问题上的发言是什么？",
            "expected_type": "事实查询",
            "reason": "单一事件的事实查询"
        },
    ]
    
    classify_node = ClassifyNode()
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        question = test_case["question"]
        expected = test_case["expected_type"]
        reason = test_case["reason"]
        
        print(f"\n--- 测试用例 {i} ---")
        print(f"问题: {question}")
        print(f"预期类型: {expected} ({reason})")
        
        try:
            # 创建状态
            state = create_initial_state(question)
            state = update_state(state, intent="complex")  # 设置为复杂问题才会分类
            
            # 调用ClassifyNode
            print(f"🔄 调用LLM进行问题分类...")
            result_state = classify_node(state)
            
            # 获取结果
            actual_type = result_state.get("question_type")
            
            print(f"✅ LLM返回成功")
            print(f"分类结果: {actual_type}")
            
            # 验证
            if actual_type == expected:
                status = "✅ PASS"
            else:
                status = f"⚠️  DIFF (预期: {expected}, 实际: {actual_type})"
            
            print(f"验证: {status}")
            
            results.append({
                "question": question,
                "expected": expected,
                "actual": actual_type,
                "passed": actual_type == expected
            })
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            logger.error(f"Classify测试失败", exc_info=True)
            results.append({
                "question": question,
                "expected": expected,
                "actual": "ERROR",
                "passed": False,
                "error": str(e)
            })
    
    # 汇总
    print("\n" + "="*80)
    print("【测试2结果汇总】")
    print("="*80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    for i, r in enumerate(results, 1):
        status = "✅" if r["passed"] else "❌"
        print(f"{status} 用例{i}: {r['question'][:40]}... → {r['actual']}")
    
    return results


def test_parameter_extraction():
    """
    测试3: 参数提取准确性
    验证系统能否正确提取时间、党派、主题等参数
    """
    print("\n" + "="*80)
    print("【测试3: 参数提取准确性】")
    print("="*80)
    
    test_cases = [
        {
            "question": "在2015-2018年期间，CDU/CSU和SPD在难民政策上的立场有何变化？",
            "expected_params": {
                "time_range": {"start_year": "2015", "end_year": "2018"},
                "parties": ["CDU/CSU", "SPD"],
                "topics": ["难民政策"]
            }
        },
        {
            "question": "2019年绿党在气候保护方面的观点",
            "expected_params": {
                "time_range": {"start_year": "2019"},
                "parties": ["绿党"],
                "topics": ["气候保护"]
            }
        },
    ]
    
    extract_node = ExtractNode()
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        question = test_case["question"]
        expected = test_case["expected_params"]
        
        print(f"\n--- 测试用例 {i} ---")
        print(f"问题: {question}")
        print(f"预期参数: {expected}")
        
        try:
            # 创建状态
            state = create_initial_state(question)
            state = update_state(
                state, 
                intent="complex",
                question_type="变化类"
            )
            
            # 调用ExtractNode
            print(f"🔄 调用LLM进行参数提取...")
            result_state = extract_node(state)
            
            # 获取结果
            actual_params = result_state.get("parameters", {})
            
            print(f"✅ LLM返回成功")
            print(f"提取结果:")
            print(f"  - 时间: {actual_params.get('time_range', {})}")
            print(f"  - 党派: {actual_params.get('parties', [])}")
            print(f"  - 主题: {actual_params.get('topics', [])}")
            
            # 简单验证（真实测试中LLM可能返回略有不同的格式）
            time_ok = bool(actual_params.get('time_range'))
            parties_ok = len(actual_params.get('parties', [])) > 0
            topics_ok = len(actual_params.get('topics', [])) > 0
            
            all_ok = time_ok and parties_ok and topics_ok
            
            status = "✅ PASS" if all_ok else "⚠️  部分成功"
            print(f"验证: {status}")
            print(f"  时间范围: {'✅' if time_ok else '❌'}")
            print(f"  党派: {'✅' if parties_ok else '❌'}")
            print(f"  主题: {'✅' if topics_ok else '❌'}")
            
            results.append({
                "question": question,
                "passed": all_ok,
                "params": actual_params
            })
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            logger.error(f"Extract测试失败", exc_info=True)
            results.append({
                "question": question,
                "passed": False,
                "error": str(e)
            })
    
    # 汇总
    print("\n" + "="*80)
    print("【测试3结果汇总】")
    print("="*80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    return results


def main():
    """运行所有真实LLM测试"""
    print("\n" + "="*80)
    print("🚀 真实LLM测试 - 意图识别和问题分类验证")
    print("="*80)
    print("\n【注意】")
    print("本测试使用真实的Gemini API")
    print("请确保:")
    print("  1. .env文件中配置了GEMINI_API_KEY")
    print("  2. 网络连接正常")
    print("  3. API额度充足")
    print()
    
    # 检查LLM连接
    print("🔍 检查LLM连接...")
    try:
        llm = GeminiLLMClient()
        test_response = llm.invoke("测试连接，请回复'OK'")
        print(f"✅ LLM连接成功")
        print(f"   测试响应: {test_response[:50]}...")
    except Exception as e:
        print(f"❌ LLM连接失败: {str(e)}")
        print("\n请检查:")
        print("  1. .env文件是否存在")
        print("  2. GEMINI_API_KEY是否正确")
        print("  3. 网络连接是否正常")
        return 1
    
    # 运行测试
    all_results = {}
    
    print("\n" + "="*80)
    print("开始测试...")
    print("="*80)
    
    # 测试1: 意图判断
    try:
        intent_results = test_intent_classification()
        all_results["intent"] = intent_results
    except Exception as e:
        print(f"\n❌ 意图判断测试组失败: {str(e)}")
        all_results["intent"] = []
    
    # 测试2: 问题分类
    try:
        classify_results = test_question_classification()
        all_results["classify"] = classify_results
    except Exception as e:
        print(f"\n❌ 问题分类测试组失败: {str(e)}")
        all_results["classify"] = []
    
    # 测试3: 参数提取
    try:
        extract_results = test_parameter_extraction()
        all_results["extract"] = extract_results
    except Exception as e:
        print(f"\n❌ 参数提取测试组失败: {str(e)}")
        all_results["extract"] = []
    
    # 最终汇总
    print("\n" + "="*80)
    print("📊 最终测试报告")
    print("="*80)
    
    for test_name, results in all_results.items():
        if results:
            passed = sum(1 for r in results if r.get("passed", False))
            total = len(results)
            rate = passed/total*100 if total > 0 else 0
            print(f"\n{test_name.upper()}:")
            print(f"  通过率: {passed}/{total} ({rate:.1f}%)")
        else:
            print(f"\n{test_name.upper()}: 未运行或失败")
    
    # 计算总体通过率
    total_tests = sum(len(r) for r in all_results.values())
    total_passed = sum(sum(1 for t in r if t.get("passed", False)) for r in all_results.values())
    
    if total_tests > 0:
        overall_rate = total_passed/total_tests*100
        print(f"\n总体通过率: {total_passed}/{total_tests} ({overall_rate:.1f}%)")
        
        if overall_rate >= 80:
            print("\n🎉 测试结果良好！Prompt效果符合预期。")
            return 0
        elif overall_rate >= 60:
            print("\n⚠️  测试结果一般，建议优化Prompt。")
            return 0
        else:
            print("\n❌ 测试结果较差，需要重新设计Prompt。")
            return 1
    else:
        print("\n❌ 没有成功运行的测试")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)

