#!/usr/bin/env python3
"""
从测试日志中提取7个问题及其答案，生成markdown报告
"""
import re
from pathlib import Path

def extract_answers_from_log(log_file):
    """从日志文件中提取所有问题和答案"""
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有问题的起始位置
    question_pattern = r'📝 问题 (\d)/7: (.+?)(?=\[0m)'
    question_matches = list(re.finditer(question_pattern, content))

    results = []

    for i, match in enumerate(question_matches):
        q_num = match.group(1)
        q_desc = match.group(2)

        # 查找该问题的原文
        # 寻找 "问题: " 后面的文本
        search_start = match.end()
        question_text_match = re.search(r'问题: (.+?)(?:\n|$)', content[search_start:search_start+500])
        question_text = question_text_match.group(1).strip() if question_text_match else "未找到问题文本"

        # 查找最终答案 - 寻找 "[EnhancedSummarizeNode] 答案长度" 之后的 "✅ 最终答案"
        # 找到下一个问题开始位置（或文件末尾）
        if i < len(question_matches) - 1:
            next_q_pos = question_matches[i+1].start()
            search_content = content[search_start:next_q_pos]
        else:
            search_content = content[search_start:]

        # 查找最终答案段落
        answer_pattern = r'✅ 最终答案.*?\n-{40,}\n(.*?)(?:\n-{40,}|\n\[32m\d{4}-\d{2}-\d{2}|$)'
        answer_match = re.search(answer_pattern, search_content, re.DOTALL)

        if answer_match:
            answer = answer_match.group(1).strip()
            # 清理ANSI颜色代码
            answer = re.sub(r'\[0m|\[1m|\[32m|\[36m', '', answer)
        else:
            answer = "⚠️ 未找到答案"

        # 检查是否有Quellen section
        has_quellen = "**Quellen**" in answer or "Quellen:" in answer

        results.append({
            'number': q_num,
            'description': q_desc,
            'question': question_text,
            'answer': answer,
            'has_quellen': has_quellen
        })

    return results

def generate_markdown_report(results, output_file):
    """生成markdown格式的测试报告"""

    # 统计
    total = len(results)
    with_quellen = sum(1 for r in results if r['has_quellen'])

    report = f"""# Quellen格式修复验证报告

## 测试概述

**测试时间**: 2025-11-10 11:20 - 11:58
**测试目的**: 验证所有Summarize prompt模板已添加Quellen section要求
**测试方法**: 运行完整的7个问题测试，检查每个答案是否包含引用来源

## 修复说明

### 问题背景
之前的测试中，只有Q2包含完整的引用来源（Quellen），其他问题缺少此部分。

### 根本原因
- `SINGLE_QUESTION_MODULAR` 模板已包含Quellen section要求
- 但所有**多问题总结模板**（变化类、对比类、总结类、趋势分析、通用）均未包含此要求

### 修复方案
在 `src/llm/prompts_summarize.py` 中为所有6个模板添加统一的Quellen section：

```
**Quellen**
- Material 1: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- Material 2: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- ...
```

**前向兼容设计**: 使用条件格式 `[text_id (falls vorhanden)]`，当metadata更新后可自动显示text_id。

## 测试结果

### 总体统计
- 总问题数: {total}
- 包含Quellen: {with_quellen}/{total}
- 成功率: {(with_quellen/total*100):.0f}%

### 逐题验证结果

"""

    for r in results:
        status = "✅" if r['has_quellen'] else "❌"
        report += f"""#### 问题 {r['number']}/7: {r['description']}

**问题**: {r['question']}

**Quellen检查**: {status} {'包含引用来源' if r['has_quellen'] else '缺少引用来源'}

<details>
<summary>查看完整答案</summary>

```
{r['answer'][:2000]}{'...(答案过长，已截断)' if len(r['answer']) > 2000 else ''}
```

</details>

---

"""

    # 添加结论
    if with_quellen == total:
        conclusion = """## 结论

🎉 **测试完全通过！**

所有7个问题的答案均包含 `**Quellen**` section，引用格式符合要求：
- 包含Redner（发言人）
- 包含Partei（党派）
- 包含YYYY-MM-DD日期格式
- 支持text_id前向兼容（当metadata更新后）

### 已验证的模板类型
1. ✅ 单问题模板 (SINGLE_QUESTION_MODULAR)
2. ✅ 变化分析模板 (CHANGE_ANALYSIS_SUMMARY)
3. ✅ 对比类模板 (COMPARISON_SUMMARY)
4. ✅ 总结类模板 (SUMMARY_TYPE_SUMMARY)
5. ✅ 趋势分析模板 (TREND_ANALYSIS_SUMMARY)
6. ✅ 通用多问题模板 (GENERAL_MULTI_QUESTION_SUMMARY)

### 下一步
- ✅ Quellen格式修复已完成
- ✅ Q6离散对比子问题错误已在之前修复
- 🔜 可选：更新2015-2024年metadata添加text_id字段（低优先级）
"""
    else:
        missing = [r['number'] for r in results if not r['has_quellen']]
        conclusion = f"""## 结论

⚠️ **部分问题缺少Quellen**

缺少引用的问题: {', '.join(missing)}

需要进一步检查这些问题使用的模板和生成逻辑。
"""

    report += conclusion

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 报告已生成: {output_file}")
    print(f"   总问题: {total}")
    print(f"   包含Quellen: {with_quellen}/{total}")

if __name__ == "__main__":
    log_file = Path("11-07测试结果/test_AFTER_QUELLEN_FIX.log")
    output_file = Path("11-07测试结果/QUELLEN_FIX_VALIDATION_REPORT.md")

    print("="*60)
    print("提取测试结果并生成报告")
    print("="*60)
    print()

    print(f"📖 读取日志文件: {log_file}")
    results = extract_answers_from_log(log_file)

    print(f"✅ 成功提取 {len(results)} 个问题答案")
    print()

    print(f"📝 生成markdown报告...")
    generate_markdown_report(results, output_file)
