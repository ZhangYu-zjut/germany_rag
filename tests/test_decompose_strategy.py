"""
问题拆解策略测试
测试智能时间拆解策略的正确性
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.templates import TemplateSelector


def test_short_term_4_years():
    """测试短期（4年）- 应该按每年拆解"""
    print("\n" + "="*60)
    print("【测试1: 短期 - 2015-2018年（4年）】")
    print("="*60)
    
    selector = TemplateSelector()
    params = {
        'time_range': {'start_year': '2015', 'end_year': '2018'},
        'parties': ['CDU/CSU', 'SPD'],
        'topics': ['难民政策']
    }
    
    sub_questions = selector.decompose('变化类', params)
    
    print(f"时间跨度: 4年")
    print(f"策略: 按每年拆解")
    print(f"预期子问题数: 2党派 × 4年 + 1对比 = 9个")
    print(f"实际子问题数: {len(sub_questions)}个")
    print(f"状态: {'✅ 通过' if len(sub_questions) == 9 else '❌ 失败'}")
    
    print(f"\n生成的子问题:")
    for i, q in enumerate(sub_questions, 1):
        print(f"  {i}. {q}")
    
    # 验证是否包含所有年份
    years = ['2015', '2016', '2017', '2018']
    for year in years:
        has_year = any(year in q for q in sub_questions)
        status = "✅" if has_year else "❌"
        print(f"\n{status} 包含{year}年的问题")
    
    return len(sub_questions) == 9


def test_short_term_5_years():
    """测试短期（5年）- 应该按每年拆解"""
    print("\n" + "="*60)
    print("【测试2: 短期边界 - 2015-2019年（5年）】")
    print("="*60)
    
    selector = TemplateSelector()
    params = {
        'time_range': {'start_year': '2015', 'end_year': '2019'},
        'parties': ['CDU/CSU'],
        'topics': ['外交政策']
    }
    
    sub_questions = selector.decompose('变化类', params)
    
    print(f"时间跨度: 5年")
    print(f"策略: 按每年拆解")
    print(f"预期子问题数: 1党派 × 5年 + 1对比 = 6个")
    print(f"实际子问题数: {len(sub_questions)}个")
    print(f"状态: {'✅ 通过' if len(sub_questions) == 6 else '❌ 失败'}")
    
    print(f"\n生成的子问题:")
    for i, q in enumerate(sub_questions, 1):
        print(f"  {i}. {q}")
    
    return len(sub_questions) == 6


def test_medium_term_9_years():
    """测试中期（9年）- 应该按2年拆解"""
    print("\n" + "="*60)
    print("【测试3: 中期 - 2010-2018年（9年）】")
    print("="*60)
    
    selector = TemplateSelector()
    params = {
        'time_range': {'start_year': '2010', 'end_year': '2018'},
        'parties': ['CDU/CSU'],
        'topics': ['气候政策']
    }
    
    sub_questions = selector.decompose('变化类', params)
    
    print(f"时间跨度: 9年")
    print(f"策略: 按2年拆解")
    print(f"预期子问题数: 1党派 × 5个采样点 + 1对比 = 6个")
    print(f"实际子问题数: {len(sub_questions)}个")
    
    print(f"\n生成的子问题:")
    for i, q in enumerate(sub_questions, 1):
        print(f"  {i}. {q}")
    
    # 验证是否按2年采样
    expected_years = ['2010', '2012', '2014', '2016', '2018']
    found_years = []
    for year in expected_years:
        if any(year in q for q in sub_questions):
            found_years.append(year)
            print(f"✅ 包含{year}年")
    
    return len(sub_questions) >= 5 and len(found_years) == 5


def test_long_term_21_years():
    """测试长期（21年）- 应该智能采样"""
    print("\n" + "="*60)
    print("【测试4: 长期 - 2000-2020年（21年）】")
    print("="*60)
    
    selector = TemplateSelector()
    params = {
        'time_range': {'start_year': '2000', 'end_year': '2020'},
        'parties': ['CDU/CSU'],
        'topics': ['外交政策']
    }
    
    sub_questions = selector.decompose('变化类', params)
    
    print(f"时间跨度: 21年")
    print(f"策略: 智能采样（约5个关键点）")
    print(f"预期子问题数: 1党派 × 5个采样点 + 1对比 ≈ 6个")
    print(f"实际子问题数: {len(sub_questions)}个")
    
    print(f"\n生成的子问题:")
    for i, q in enumerate(sub_questions, 1):
        print(f"  {i}. {q}")
    
    # 验证子问题数量是否合理（应该远小于21）
    return len(sub_questions) <= 10


def test_multiple_parties():
    """测试多党派情况"""
    print("\n" + "="*60)
    print("【测试5: 多党派 - 3个党派 × 4年】")
    print("="*60)
    
    selector = TemplateSelector()
    params = {
        'time_range': {'start_year': '2015', 'end_year': '2018'},
        'parties': ['CDU/CSU', 'SPD', 'Grüne'],
        'topics': ['环境政策']
    }
    
    sub_questions = selector.decompose('变化类', params)
    
    print(f"时间跨度: 4年")
    print(f"党派数: 3个")
    print(f"策略: 按每年拆解")
    print(f"预期子问题数: 3党派 × 4年 + 1对比 = 13个")
    print(f"实际子问题数: {len(sub_questions)}个")
    print(f"状态: {'✅ 通过' if len(sub_questions) == 13 else '❌ 失败'}")
    
    print(f"\n生成的子问题（前5个）:")
    for i, q in enumerate(sub_questions[:5], 1):
        print(f"  {i}. {q}")
    print(f"  ... (共{len(sub_questions)}个)")
    
    return len(sub_questions) == 13


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("智能拆解策略测试")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("短期4年", test_short_term_4_years()))
    results.append(("短期5年边界", test_short_term_5_years()))
    results.append(("中期9年", test_medium_term_9_years()))
    results.append(("长期21年", test_long_term_21_years()))
    results.append(("多党派", test_multiple_parties()))
    
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
        print("\n🎉 所有测试通过！")
        print("\n智能拆解策略验证成功：")
        print("  ✅ 短期（≤5年）：按每年拆解")
        print("  ✅ 中期（6-10年）：按2年拆解")
        print("  ✅ 长期（>10年）：智能采样")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

